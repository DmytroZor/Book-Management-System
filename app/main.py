from fastapi import FastAPI
from app import models
from app.db import engine
from app.routers import books, auth
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.errors import AppError

app = FastAPI()


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logging.error(f"AppError: {exc.message} | Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "details": str(exc),
            "path": str(request.url.path)
        },
    )


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.on_event("startup")
async def on_startup():
    await init_models()


app.include_router(auth.router)
app.include_router(books.router)
