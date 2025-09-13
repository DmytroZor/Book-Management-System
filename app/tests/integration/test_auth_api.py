import pytest

@pytest.mark.asyncio
async def test_register_and_login(client_fixture):
    # Реєстрація користувача
    resp = await client_fixture.post("/auth/register", json={
        "username": "testuser",
        "password": "secret123",
        "email": "user@test.com"
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    assert token

    # Логін користувача
    resp = await client_fixture.post(
        "/auth/login",
        data={"username": "testuser", "password": "secret123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
