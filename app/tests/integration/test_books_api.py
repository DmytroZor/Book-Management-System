import pytest

@pytest.mark.asyncio
async def test_books_crud(client_fixture):
    resp = await client_fixture.post("/auth/register", json={
        "username": "booker",
        "password": "secret123",
        "email": "book@test.com"
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client_fixture.post("/books/", json={
        "title": "My Book",
        "genre": "Fiction",
        "published_year": 2022,
        "authors": ["Author1"]
    }, headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    book_id = body["id"]
    assert body["title"] == "My Book"
    assert isinstance(body["authors"], list)
    assert any(a["name"] == "Author1" for a in body["authors"])

    resp = await client_fixture.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Book"

    resp = await client_fixture.put(f"/books/{book_id}", json={"title": "Updated Book"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Book"

    resp = await client_fixture.get("/books/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(b["id"] == book_id for b in resp.json())

    resp = await client_fixture.delete(f"/books/{book_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("message") == "Book deleted"
