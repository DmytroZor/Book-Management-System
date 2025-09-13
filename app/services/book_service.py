from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Book, Author
from typing import List, Optional


async def create_book(db: AsyncSession, title: str, genre: str, published_year: int, authors: List[str]):
    author_objs = []
    for name in authors:
        q = await db.execute(select(Author).where(Author.name == name))
        author = q.scalar_one_or_none()
        if not author:
            author = Author(name=name)
            db.add(author)
        author_objs.append(author)

    book = Book(title=title, genre=genre, published_year=published_year, authors=author_objs)
    db.add(book)
    await db.commit()

    q = await db.execute(select(Book).options(selectinload(Book.authors)).where(Book.id == book.id))
    book_with_authors = q.scalar_one()
    return book_with_authors


async def get_books(
        db: AsyncSession,
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
    stmt = select(Book).options(selectinload(Book.authors))

    if title:
        stmt = stmt.where(Book.title.ilike(f"%{title}%"))
    if genre:
        stmt = stmt.where(Book.genre == genre)
    if year_from:
        stmt = stmt.where(Book.published_year >= year_from)
    if year_to:
        stmt = stmt.where(Book.published_year <= year_to)
    if author:
        # join through authors
        stmt = stmt.join(Book.authors).where(Author.name.ilike(f"%{author}%"))

    if sort_by not in ("title", "published_year"):
        sort_by = "title"
    sort_col = getattr(Book, sort_by)
    if order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_book_by_id(db: AsyncSession, book_id: int):
    q = await db.execute(select(Book).options(selectinload(Book.authors)).where(Book.id == book_id))
    return q.scalar_one_or_none()


async def update_book(db: AsyncSession, book_id: int, data: dict):
    book = await get_book_by_id(db, book_id)
    if not book:
        return None
    if "authors" in data:

        new_authors = []
        for name in data["authors"]:
            q = await db.execute(select(Author).where(Author.name == name))
            author = q.scalar_one_or_none()
            if not author:
                author = Author(name=name)
                db.add(author)
            new_authors.append(author)
        book.authors = new_authors

    for k, v in data.items():
        if k == "genre" and v is not None:
            setattr(book, k, v.value if hasattr(v, "value") else v)
        elif k == "published_year" and v is not None:
            setattr(book, k, v)
        elif k == "title" and v is not None:
            setattr(book, k, v)

    await db.commit()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book_id: int) -> bool:
    book = await get_book_by_id(db, book_id)
    if not book:
        return False
    await db.delete(book)
    await db.commit()
    return True
