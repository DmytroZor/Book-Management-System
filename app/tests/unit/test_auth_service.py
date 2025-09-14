import pytest
from app.services import auth_service

def test_password_hash_and_verify():
    password = "secret123"
    hashed = auth_service.hash_password(password)
    assert auth_service.verify_password(password, hashed)
    assert not auth_service.verify_password("wrongpass", hashed)


def test_create_and_decode_token():
    data = {"sub": "testuser"}
    token = auth_service.create_access_token(data, expires_seconds=60)
    decoded = auth_service.decode_token(token)
    assert decoded["sub"] == "testuser"
    assert "exp" in decoded
