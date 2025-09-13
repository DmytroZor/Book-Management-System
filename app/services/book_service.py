from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Book, Author
from typing import List

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
    await db.refresh(book)
    return book

async def get_books(db: AsyncSession):
    q = await db.execute(select(Book).options(selectinload(Book.authors)))
    return q.scalars().all()
