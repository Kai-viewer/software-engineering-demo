import os
from contextlib import asynccontextmanager
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


@asynccontextmanager
async def lifespan(app):
    app.state.pool = AsyncConnectionPool(
        conninfo=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/submissions'),
        kwargs={'row_factory': dict_row}, open=False,
    )
    await app.state.pool.open()
    try:
        await app.state.pool.wait(timeout=10)
        yield
    finally:
        await app.state.pool.close()


async def get_db(request: Request):
    async with request.app.state.pool.connection() as connection:
        yield connection
