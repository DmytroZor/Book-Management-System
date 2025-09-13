from passlib.hash import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User


def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.verify(plain, hashed)


def create_access_token(data: dict, expires_seconds: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=(expires_seconds or settings.jwt_expiration))
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise


async def get_user_by_username(db: AsyncSession, username: str):
    q = await db.execute(select(User).where(User.username == username))
    return q.scalar_one_or_none()

async def create_user(db: AsyncSession, username: str, password: str, email: str | None = None):
    user = User(username=username, email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
