# Book-Management-System

1. Create & activate venv
2. Install requirements: `pip install -r requirements.txt`
3. Start Postgres
4. Set `.env` DATABASE_URL (e.g. `postgresql+asyncpg://postgres:password@localhost/books_db`)
5. Run Alembic migrations:
   `alembic -c migrations/alembic.ini upgrade head`
6. Run server:
   `uvicorn app.main:app --reload`
7. Run tests:
   `pip install aiosqlite`
   `pytest -v`