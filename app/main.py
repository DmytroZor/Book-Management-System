from fastapi import FastAPI
import models
from db import engine

app = FastAPI()

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

async def on_startup():
    await init_models()
