import pytest

@pytest.mark.asyncio
async def test_books_crud(client_fixture):

    resp = await client_fixture.post("/auth/register", json={
        "username": "booker",
        "password": "secret123",
        "email": "book@test.com"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    resp = await client_fixture.post("/books/", json={
        "title": "My Book",
        "genre": "Fiction",
        "published_year": 2022,
        "authors": ["Author1"]
    }, headers=headers)
    assert resp.status_code == 201
    book_id = resp.json()["id"]


    resp = await client_fixture.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Book"

    resp = await client_fixture.put(
        f"/books/{book_id}",
        json={
            "title": "Updated Book",
            "genre": "Fiction",
            "published_year": 2022,
            "authors": ["Author1"]
        },
        headers=headers
    )

    resp = await client_fixture.get("/books/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client_fixture.delete(f"/books/{book_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Book deleted"
