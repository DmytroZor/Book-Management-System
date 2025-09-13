from fastapi import FastAPI
from app import models
from app.db import engine
from app.routers import books, auth

app = FastAPI()

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await init_models()
app.include_router(auth.router)
app.include_router(books.router)

for route in app.routes:
    print(route.path, route.methods)