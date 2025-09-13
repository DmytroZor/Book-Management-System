from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.book_schema import BookCreate, BookOut
from app.services.book_service import create_book, get_books
from app.db import get_db

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/", response_model=BookOut)
async def api_create_book(book: BookCreate, db: AsyncSession = Depends(get_db)):
    return await create_book(db, book.title, book.genre.value, book.published_year, book.authors)

@router.get("/", response_model=list[BookOut])
async def api_get_books(db: AsyncSession = Depends(get_db)):
    return await get_books(db)
