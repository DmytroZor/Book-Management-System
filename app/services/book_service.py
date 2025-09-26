from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from typing import List, Optional
from app.errors import AppError
from fastapi import status
import datetime
from app.schemas.book_schema import SortField, SortOrder




async def _ensure_author_and_get_id(conn: AsyncConnection, name: str) -> int:
    name = (name or "").strip()
    if not name:
        raise AppError("Invalid author name", status_code=status.HTTP_400_BAD_REQUEST, details={"name": name})
    q = await conn.execute(text("SELECT id FROM authors WHERE name = :name"), {"name": name})
    row = q.mappings().first()
    if row:
        return row["id"]
    await conn.execute(text("INSERT INTO authors (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"), {"name": name})
    q2 = await conn.execute(text("SELECT id FROM authors WHERE name = :name"), {"name": name})
    row2 = q2.mappings().first()
    if row2:
        return row2["id"]
    raise AppError("Failed to create author", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _try_insert_book_author(conn: AsyncConnection, book_id: int, author_id: int):
    await conn.execute(
        text("INSERT INTO book_authors (book_id, author_id) VALUES (:b, :a) ON CONFLICT DO NOTHING"),
        {"b": book_id, "a": author_id}
    )


async def create_book(conn: AsyncConnection, title: str, genre: str, published_year: int, authors: List[str]):
    if not title or not title.strip():
        raise AppError("Invalid title", status_code=status.HTTP_400_BAD_REQUEST)
    now_year = datetime.datetime.now().year
    if published_year is None or not (1800 <= int(published_year) <= now_year):
        raise AppError("Invalid published_year", status_code=status.HTTP_400_BAD_REQUEST)
    r = await conn.execute(
        text(
            "INSERT INTO books (title, genre, published_year) "
            "VALUES (:title, :genre, :year) RETURNING id, title, genre, published_year"
        ),
        {"title": title.strip(), "genre": genre, "year": published_year}
    )
    book_row = r.mappings().first()
    if not book_row:
        raise AppError("Failed to create book", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    book_id = book_row["id"]
    result_authors = []
    for name in authors or []:
        name = (name or "").strip()
        if not name:
            continue
        author_id = await _ensure_author_and_get_id(conn, name)
        await _try_insert_book_author(conn, book_id, author_id)
        result_authors.append({"id": author_id, "name": name})
    await conn.commit()
    return {
        "id": book_id,
        "title": book_row["title"],
        "genre": book_row["genre"],
        "published_year": book_row["published_year"],
        "authors": result_authors,
    }


async def _load_authors_for_book_ids(conn: AsyncConnection, book_ids: List[int]) -> dict:
    if not book_ids:
        return {}
    placeholders = []
    params = {}
    for i, bid in enumerate(book_ids):
        key = f"id{i}"
        placeholders.append(f":{key}")
        params[key] = bid
    sql = (
        "SELECT ba.book_id, a.id as author_id, a.name "
        "FROM book_authors ba "
        "JOIN authors a ON a.id = ba.author_id "
        f"WHERE ba.book_id IN ({', '.join(placeholders)})"
    )
    q = await conn.execute(text(sql), params)
    rows = q.mappings().all()
    mapping: dict = {}
    for r in rows:
        bid = r["book_id"]
        mapping.setdefault(bid, []).append({"id": r["author_id"], "name": r["name"]})
    return mapping


async def get_books(
    conn: AsyncConnection,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sort_by: str = "title",
    order: str = "asc",
    limit: int = 10,
    offset: int = 0,
):
    allowed_sort_fields = SortField
    allowed_orders = SortOrder
    sort_by = sort_by if sort_by in allowed_sort_fields else "title"
    order = order if order in allowed_orders else "asc"
    clauses = []
    params = {}
    if title:
        clauses.append("b.title ILIKE :title")
        params["title"] = f"%{title}%"
    if genre:
        clauses.append("b.genre = :genre")
        params["genre"] = genre
    if year_from:
        clauses.append("b.published_year >= :year_from")
        params["year_from"] = year_from
    if year_to:
        clauses.append("b.published_year <= :year_to")
        params["year_to"] = year_to
    base_where = " AND ".join(clauses) if clauses else "1=1"
    if author:
        sql = (
            f"SELECT DISTINCT b.id, b.title, b.genre, b.published_year "
            f"FROM books b "
            f"JOIN book_authors ba ON ba.book_id = b.id "
            f"JOIN authors a ON a.id = ba.author_id "
            f"WHERE {base_where} AND a.name ILIKE :author "
            f"ORDER BY {sort_by} {order} LIMIT :limit OFFSET :offset"
        )
        params.update({"author": f"%{author}%", "limit": limit, "offset": offset})
    else:
        sql = (
            f"SELECT b.id, b.title, b.genre, b.published_year "
            f"FROM books b WHERE {base_where} "
            f"ORDER BY {sort_by} {order} LIMIT :limit OFFSET :offset"
        )
        params.update({"limit": limit, "offset": offset})
    q = await conn.execute(text(sql), params)
    books = [dict(r) for r in q.mappings().all()]
    book_ids = [b["id"] for b in books]
    authors_map = await _load_authors_for_book_ids(conn, book_ids)
    for b in books:
        b["authors"] = authors_map.get(b["id"], [])
    return books


async def get_book_by_id(conn: AsyncConnection, book_id: int):
    q = await conn.execute(text("SELECT id, title, genre, published_year FROM books WHERE id = :id"), {"id": book_id})
    row = q.mappings().first()
    if not row:
        return None
    row_d = dict(row)
    authors_map = await _load_authors_for_book_ids(conn, [book_id])
    row_d["authors"] = authors_map.get(book_id, [])
    return row_d


async def update_book(conn: AsyncConnection, book_id: int, data: dict):
    book = await get_book_by_id(conn, book_id)
    if not book:
        return None
    if "authors" in data:
        authors_val = data["authors"]
        if authors_val is None:
            await conn.execute(text("DELETE FROM book_authors WHERE book_id = :id"), {"id": book_id})
        else:
            if not isinstance(authors_val, list) or any(not isinstance(n, str) for n in authors_val):
                raise AppError("Invalid authors format", status_code=status.HTTP_400_BAD_REQUEST, details={"authors": authors_val})
            await conn.execute(text("DELETE FROM book_authors WHERE book_id = :id"), {"id": book_id})
            for name in authors_val:
                name = (name or "").strip()
                if not name:
                    continue
                author_id = await _ensure_author_and_get_id(conn, name)
                await _try_insert_book_author(conn, book_id, author_id)
    if "title" in data and data["title"] is not None:
        t = (data["title"] or "").strip()
        if not t:
            raise AppError("Invalid title", status_code=status.HTTP_400_BAD_REQUEST)
        await conn.execute(text("UPDATE books SET title = :t WHERE id = :id"), {"t": t, "id": book_id})
    if "genre" in data and data["genre"] is not None:
        g = data["genre"]
        await conn.execute(text("UPDATE books SET genre = :g WHERE id = :id"), {"g": g, "id": book_id})
    if "published_year" in data and data["published_year"] is not None:
        try:
            y = int(data["published_year"])
        except Exception:
            raise AppError("Invalid published_year", status_code=status.HTTP_400_BAD_REQUEST)
        await conn.execute(text("UPDATE books SET published_year = :y WHERE id = :id"), {"y": y, "id": book_id})
    await conn.commit()
    return await get_book_by_id(conn, book_id)


async def delete_book(conn: AsyncConnection, book_id: int) -> bool:
    exists = await get_book_by_id(conn, book_id)
    if not exists:
        return False
    await conn.execute(text("DELETE FROM book_authors WHERE book_id = :id"), {"id": book_id})
    await conn.execute(text("DELETE FROM books WHERE id = :id"), {"id": book_id})
    await conn.commit()
    return True


async def bulk_create_books(conn: AsyncConnection, books_data: list[dict]):
    if not books_data:
        raise AppError("No books provided for import", status_code=status.HTTP_400_BAD_REQUEST)
    created = []
    try:
        for data in books_data:
            title = (data.get("title") or "").strip()
            if not title:
                raise AppError("Invalid title", status_code=status.HTTP_400_BAD_REQUEST, details={"book": data})
            py = data.get("published_year")
            published_year = None
            if py is not None and py != "":
                try:
                    published_year = int(py)
                except Exception:
                    raise AppError(f"Invalid published_year: {py}", status_code=status.HTTP_400_BAD_REQUEST, details={"book": data})
            genre = data.get("genre")
            r = await conn.execute(
                text("INSERT INTO books (title, genre, published_year) VALUES (:title, :genre, :year) RETURNING id"),
                {"title": title, "genre": genre, "year": published_year},
            )
            book_id = r.scalar_one()
            authors_list = []
            for name in data.get("authors", []):
                name = (name or "").strip()
                if not name:
                    continue
                author_id = await _ensure_author_and_get_id(conn, name)
                await _try_insert_book_author(conn, book_id, author_id)
                authors_list.append({"id": author_id, "name": name})
            created.append({"id": book_id, "title": title, "genre": genre, "published_year": published_year, "authors": authors_list})
        await conn.commit()
    except AppError:
        raise
    except Exception as e:
        await conn.rollback()
        raise AppError("Database error while bulk creating books", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details={"reason": str(e)})
    return created
