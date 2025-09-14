from fastapi import APIRouter, Depends, UploadFile, Request, Query, status
from typing import List, Optional, Literal
from sqlalchemy.ext.asyncio import AsyncConnection
from app.db import get_conn
from app.schemas.book_schema import BookCreate, BookOut, BookUpdate, SortField, SortOrder, MessageResponse, Genre, AuthorOut
from app.services import book_service
from app.limiter import limiter
from fastapi.responses import StreamingResponse
import csv, io, json
from pydantic import BaseModel
from app.routers.auth import get_current_user
from app.errors import NotFoundError, AppError, UnauthorizedError

router = APIRouter(prefix="/books", tags=["Books"])


def book_to_out(book: dict) -> BookOut:
    authors = []
    for a in book.get("authors", []):
        if isinstance(a, dict):
            aid = int(a.get("id") or 0)
            name = a.get("name") or ""
        else:
            aid = 0
            name = str(a)
        authors.append({"id": aid, "name": name})
    data = {
        "id": int(book["id"]),
        "title": book["title"],
        "genre": book.get("genre"),
        "published_year": int(book["published_year"]) if book.get("published_year") is not None else None,
        "authors": authors,
    }
    return BookOut.model_validate(data)


@router.get("/export")
async def export_books(
    format: Literal["json", "csv"] = Query("json"),
    conn: AsyncConnection = Depends(get_conn)
):
    books = await book_service.get_books(conn, limit=10000, offset=0)
    rows = []
    for b in books:
        rows.append({
            "id": b["id"],
            "title": b["title"],
            "genre": b["genre"],
            "published_year": b["published_year"],
            "authors": ";".join([a["name"] for a in b.get("authors", [])])
        })

    if format == "json":
        data = json.dumps(rows, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(data.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=books.json"}
        )
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "title", "genre", "published_year", "authors"])
        writer.writeheader()
        writer.writerows(rows)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=books.csv"}
        )


@router.post("/", response_model=BookOut, status_code=201)
async def create_book(book: BookCreate, conn: AsyncConnection = Depends(get_conn), user=Depends(get_current_user)):
    created = await book_service.create_book(
        conn,
        title=book.title,
        genre=book.genre.value if hasattr(book.genre, "value") else book.genre,
        published_year=book.published_year,
        authors=book.authors,
    )
    return book_to_out(created)


@router.get("/", response_model=List[BookOut])
@limiter.limit("20/minute")
async def list_books(
        request: Request,
        title: Optional[str] = None,
        author: Optional[str] = None,
        genre: Optional[Genre] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        sort_by: SortField = SortField.title,
        order: SortOrder = SortOrder.asc,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=50),
        conn: AsyncConnection = Depends(get_conn)
):
    books = await book_service.get_books(
        conn,
        title=title,
        author=author,
        genre=genre.value if genre else None,
        year_from=year_from,
        year_to=year_to,
        sort_by=sort_by.value,
        order=order.value,
        limit=limit,
        offset=skip
    )
    return [book_to_out(b) for b in books]


@router.get("/{book_id}", response_model=BookOut)
async def get_book(book_id: int, conn: AsyncConnection = Depends(get_conn)):
    book = await book_service.get_book_by_id(conn, book_id)
    if not book:
        raise NotFoundError("Book", book_id)
    return book_to_out(book)


@router.put("/{book_id}", response_model=BookOut)
async def update_book(book_id: int, payload: BookUpdate, conn: AsyncConnection = Depends(get_conn),
                      user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise AppError(message="No fields provided for update", status_code=status.HTTP_400_BAD_REQUEST, details={"book_id": book_id})
    if "genre" in data and data["genre"] is not None:
        data["genre"] = data["genre"].value if hasattr(data["genre"], "value") else data["genre"]
    updated = await book_service.update_book(conn, book_id, data)
    if not updated:
        raise NotFoundError("Book", book_id)
    return book_to_out(updated)


@router.delete("/{book_id}", response_model=MessageResponse)
async def delete_book(book_id: int, conn: AsyncConnection = Depends(get_conn), user=Depends(get_current_user)):
    ok = await book_service.delete_book(conn, book_id)
    if not ok:
        raise NotFoundError("Book", book_id)
    return MessageResponse(message="Book deleted")


class BookImportPayload(BaseModel):
    books: List[BookCreate]


@router.post("/import")
async def import_books(
    file: UploadFile,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict = Depends(get_current_user),
):
    if not current_user:
        raise UnauthorizedError()

    try:
        if file.filename.endswith(".json"):
            data = json.loads((await file.read()).decode("utf-8"))

        elif file.filename.endswith(".csv"):
            content = (await file.read()).decode("utf-8").splitlines()
            reader = csv.DictReader(content)
            data = [dict(row) for row in reader]

            for d in data:
                if "authors" in d and isinstance(d["authors"], str):
                    d["authors"] = [a.strip() for a in d["authors"].split(";") if a.strip()]

        else:
            raise AppError(
                message="Unsupported file format. Only JSON and CSV are allowed.",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"filename": file.filename}
            )

        books = await book_service.bulk_create_books(conn, data)
        return {"imported": len(books)}

    except AppError:
        raise
    except Exception as e:
        raise AppError(
            message="Failed to save books to database",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"reason": str(e)}
        )
