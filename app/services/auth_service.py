from passlib.hash import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.exc import IntegrityError
from fastapi import status
from app.errors import AppError


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.verify(plain, hashed)


def create_access_token(data: dict, expires_seconds: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(seconds=(expires_seconds or settings.jwt_expiration))
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise


async def get_user_by_username(conn: AsyncConnection, username: str) -> dict | None:
    q = await conn.execute(text("SELECT id, username, email, hashed_password FROM users WHERE username = :username"), {"username": username})
    row = q.mappings().first()
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"], "hashed_password": row["hashed_password"]}


async def create_user(conn: AsyncConnection, username: str, password: str, email: str | None = None) -> dict:
    if not username or not username.strip():
        raise AppError("Invalid username", status_code=status.HTTP_400_BAD_REQUEST)
    hashed = hash_password(password)
    try:
        r = await conn.execute(
            text("INSERT INTO users (username, email, hashed_password) VALUES (:username, :email, :hpw) RETURNING id, username, email"),
            {"username": username.strip(), "email": email, "hpw": hashed}
        )
        row = r.mappings().first()
        if not row:
            raise AppError("Failed to create user", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        await conn.commit()
        return {"id": row["id"], "username": row["username"], "email": row["email"], "hashed_password": hashed}
    except IntegrityError:
        await conn.rollback()
        raise AppError("Username already registered", status_code=status.HTTP_400_BAD_REQUEST)
