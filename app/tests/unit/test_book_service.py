import pytest
from app.services import book_service

@pytest.mark.asyncio
async def test_create_book(db_conn):
    book = await book_service.create_book(
        db_conn,
        title="Test Book",
        genre="Fiction",
        published_year=2020,
        authors=["Author One", "Author Two"],
    )
    assert book["id"] is not None
    assert book["title"] == "Test Book"
    assert isinstance(book["authors"], list)
    assert len(book["authors"]) == 2

@pytest.mark.asyncio
async def test_bulk_create_and_query(db_conn):
    data = [
        {"title": "Bulk A", "genre": "Science", "published_year": 2001, "authors": ["A1", "A2"]},
        {"title": "Bulk B", "genre": "History", "published_year": 1999, "authors": ["B1"]}
    ]
    created = await book_service.bulk_create_books(db_conn, data)
    assert len(created) == 2
    books = await book_service.get_books(db_conn, limit=50)
    assert any(b["title"] == "Bulk A" for b in books)
    assert any(b["title"] == "Bulk B" for b in books)
