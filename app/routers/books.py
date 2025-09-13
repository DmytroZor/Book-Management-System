from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas.book_schema import BookCreate, BookOut, BookUpdate, SortField, SortOrder, MessageResponse, Genre
from app.services import book_service
from app.services.auth_service import decode_token
from app.services.auth_service import get_user_by_username
from app.limiter import limiter
from fastapi.responses import StreamingResponse
import csv, io, json
from pydantic import ValidationError, BaseModel
from fastapi import FastAPI
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from app.routers.auth import get_current_user


router = APIRouter(prefix="/books", tags=["Books"])


def book_to_out(book) -> BookOut:

    authors = []
    if getattr(book, "authors", None):

        authors = [a.name for a in book.authors]


    genre_value = getattr(book, "genre", None)
    try:

        genre_value = genre_value.value if hasattr(genre_value, "value") else genre_value
    except Exception:
        pass

    data = {
        "id": int(book.id),
        "title": book.title,
        "genre": genre_value,
        "published_year": int(book.published_year),
        "authors": authors,
    }

    return BookOut.model_validate(data)



@router.post("/", response_model=BookOut, status_code=201)
async def create_book(book: BookCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    created = await book_service.create_book(
        db,
        title=book.title,
        genre=book.genre,
        published_year=book.published_year,
        authors=book.authors,
    )
    return created


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
        db: AsyncSession = Depends(get_db)
):
    books = await book_service.get_books(
        db,
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
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await book_service.get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_to_out(book)


@router.put("/{book_id}", response_model=BookOut)
async def update_book(book_id: int, payload: BookUpdate, db: AsyncSession = Depends(get_db),
                      user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    updated = await book_service.update_book(db, book_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_to_out(updated)


@router.delete("/{book_id}", response_model=MessageResponse)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    ok = await book_service.delete_book(db, book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return MessageResponse(message="Book deleted")


# @router.post("/import", response_model=MessageResponse)
# async def import_books(
#         file: UploadFile = File(...),
#         db: AsyncSession = Depends(get_db),
#         user = Depends(get_current_user)
# ):
#     content = await file.read()
#     if file.filename.endswith(".json"):
#         books_data = json.loads(content)
#     elif file.filename.endswith(".csv"):
#         reader = csv.DictReader(io.StringIO(content.decode()))
#         books_data = [row for row in reader]
#     else:
#         raise HTTPException(status_code=400, detail="Unsupported file format")
#
#
#     count = 0
#     for raw in books_data:
#         try:
#
#             if isinstance(raw.get("authors"), str):
#                 authors = [a.strip() for a in raw["authors"].split(",") if a.strip()]
#             else:
#                 authors = raw.get("authors") or []
#             payload = BookCreate(
#                 title=raw["title"],
#                 genre=raw["genre"],
#                 published_year=int(raw["published_year"]),
#                 authors=authors
#             )
#         except Exception as e:
#             continue
#         await book_service.create_book(db, payload)
#         count += 1
#
#     return MessageResponse(message=f"Imported {count} books")


class BookImportPayload(BaseModel):
    books: List[BookCreate]


@router.post("/import", response_model=Dict[str, Any])
async def import_books_optimized(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    content = await file.read()
    books_data = []
    errors = []

    if file.filename.endswith(".json"):
        raw_data = json.loads(content)
    elif file.filename.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content.decode()))
        raw_data = [row for row in reader]
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    for raw in raw_data:
        try:
            if isinstance(raw.get("authors"), str):
                raw["authors"] = [a.strip() for a in raw["authors"].split(",") if a.strip()]

            books_data.append(BookCreate(**raw))
        except ValidationError as e:
            errors.append({"record": raw, "error": e.errors()})
        except Exception as e:
            errors.append({"record": raw, "error": str(e)})

    if books_data:
        try:

            count = await book_service.bulk_create_books(db, books_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to save books to database")
    else:
        count = 0

    return {
        "message": f"Successfully imported {count} books. {len(errors)} records failed to import.",
        "imported_count": count,
        "failed_count": len(errors),
        "errors": errors
    }


@router.get("/export")
async def export_books(format: str = Query("json", regex="^(json|csv)$"), db: AsyncSession = Depends(get_db)):
    books = await book_service.get_books(db, limit=10000, offset=0)  # export up to some reasonable limit
    rows = []
    for b in books:
        rows.append({
            "id": b.id,
            "title": b.title,
            "genre": b.genre,
            "published_year": b.published_year,
            "authors": ",".join([a.name for a in b.authors])
        })

    if format == "json":
        data = json.dumps(rows, ensure_ascii=False, indent=2)
        return StreamingResponse(io.BytesIO(data.encode("utf-8")), media_type="application/json",
                                 headers={"Content-Disposition": "attachment; filename=books.json"})
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "title", "genre", "published_year", "authors"])
        writer.writeheader()
        writer.writerows(rows)
        return StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8")), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=books.csv"})
