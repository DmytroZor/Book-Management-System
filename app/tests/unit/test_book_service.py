import pytest
from app.services import book_service

@pytest.mark.asyncio
async def test_create_book(db_session):
    book = await book_service.create_book(
        db_session,
        title="Test Book",
        genre="Fiction",
        published_year=2020,
        authors=["Author One", "Author Two"],
    )
    assert book.id is not None
    assert book.title == "Test Book"
    assert len(book.authors) == 2
