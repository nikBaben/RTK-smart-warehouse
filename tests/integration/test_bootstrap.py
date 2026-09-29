from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, inspect, select

from backend.db.base import Base
from backend import dev_bootstrap
from backend.models.product import Product
from backend.models.warehouse import Warehouse

pytestmark = pytest.mark.integration


async def test_migrations_create_current_schema_from_empty_database(sessions):
    def migrate(connection):
        Base.metadata.drop_all(connection)
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        scripts = ScriptDirectory.from_config(config)
        revisions = list(reversed(list(scripts.walk_revisions())))
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        with Operations.context(context):
            for revision in revisions:
                revision.module.upgrade()
            assert compare_metadata(context, Base.metadata) == []
            for revision in reversed(revisions):
                revision.module.downgrade()
            assert inspect(connection).get_table_names() == []
            for revision in revisions:
                revision.module.upgrade()

    async with sessions() as session, session.begin():
        connection = await session.connection()
        await connection.run_sync(migrate)


async def test_demo_seed_preserves_changes_on_restart(sessions, monkeypatch):
    monkeypatch.setattr(dev_bootstrap, "async_session", sessions)
    await dev_bootstrap.seed_warehouse()
    async with sessions() as session, session.begin():
        warehouse = await session.get(Warehouse, "DEV-WH-1")
        total = await session.scalar(select(func.sum(Product.stock)))
        assert warehouse.products_count == total == 180
        assert await session.scalar(select(func.count()).select_from(Warehouse)) == 2
        warehouse.name = "Изменён пользователем"
    await dev_bootstrap.seed_warehouse()
    async with sessions() as session:
        assert (
            await session.get(Warehouse, "DEV-WH-1")
        ).name == "Изменён пользователем"
        assert await session.scalar(select(func.count()).select_from(Product)) == 3
