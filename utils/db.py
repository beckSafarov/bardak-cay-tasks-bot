import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def create_db_pool() -> asyncpg.Pool:
    """Create and return a PostgreSQL connection pool."""
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL environment variable")

    return await asyncpg.create_pool(
        dsn=DATABASE_URL,
        statement_cache_size=0,
    )

async def close_db_pool(pool: asyncpg.Pool) -> None:
    """Close the database connection pool."""
    if pool is not None:
        await pool.close()
