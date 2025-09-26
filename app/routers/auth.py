# app/routers/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncConnection
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError

from app.db import get_conn
from app.schemas.auth_schema import UserCreate, Token
from app.services import auth_service
from app.errors import AppError, UnauthorizedError, NotFoundError
from app.routers.utils import get_common_responses

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    responses=(lambda: {**get_common_responses(), 400: {"model": __import__("app.schemas.error_schema", fromlist=["ErrorResponse"]).ErrorResponse, "description": "Username already registered"}})()
)
async def register(user: UserCreate, conn: AsyncConnection = Depends(get_conn)):
    existing = await auth_service.get_user_by_username(conn, user.username)
    if existing:
        raise AppError("Username already registered", status_code=status.HTTP_400_BAD_REQUEST)

    new_user = await auth_service.create_user(conn, user.username, user.password, user.email)
    token = auth_service.create_access_token({"sub": new_user["username"]})
    return {"access_token": token, "token_type": "bearer"}


# @router.post(
#     "/login",
#     response_model=Token,
#     responses=get_common_responses()
# )
# async def login(form_data: OAuth2PasswordRequestForm = Depends(), conn: AsyncConnection = Depends(get_conn)):
#     user = await auth_service.get_user_by_username(conn, form_data.username)
#     if not user or not auth_service.verify_password(form_data.password, user["hashed_password"]):
#         raise UnauthorizedError()
#     token = auth_service.create_access_token({"sub": user["username"]})
#     return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme), conn: AsyncConnection = Depends(get_conn)):
    try:
        payload = auth_service.decode_token(token)
    except JWTError:
        raise UnauthorizedError()

    username: str | None = payload.get("sub")
    if username is None:
        raise UnauthorizedError()

    user = await auth_service.get_user_by_username(conn, username)
    if user is None:
        raise NotFoundError("User", username)

    user.pop("hashed_password", None)
    return user
