"""Lazy database setup: importing services or the API never opens/configures a DB."""

from functools import lru_cache
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from backend.core.config import settings


@lru_cache(maxsize=1)
def get_engine():
    if not settings.DB_URL:
        raise RuntimeError("DB_URL is required to access the database")
    return create_async_engine(
        settings.DB_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE_SEC,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )


def async_session() -> AsyncSession:
    return async_sessionmaker(get_engine(), expire_on_commit=False)()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
