import os
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.db.base import Base
import backend.models  # noqa: F401 -- registers every table in Base.metadata


@pytest.fixture
async def sessions():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set TEST_DATABASE_URL to a disposable PostgreSQL database named rtk_test*"
        )
    if not (make_url(url).database or "").startswith("rtk_test"):
        pytest.fail("Integration tests require a dedicated rtk_test* database")
    schema = "test_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_async_engine(
        url, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        await admin.dispose()
