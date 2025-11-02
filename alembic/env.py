from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base
import app.models  # важно: чтобы подхватить все модели

config = context.config

# --- URL БД ---
db_url = (
    getattr(settings, "DB_URL", None)
    or getattr(settings, "DATABASE_URL", None)
    or getattr(settings, "SQLALCHEMY_DATABASE_URI", None)
)
if not db_url:
    raise RuntimeError("DB URL not found (DB_URL / DATABASE_URL / SQLALCHEMY_DATABASE_URI)")

config.set_main_option("sqlalchemy.url", db_url)

# --- logging ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# --- НЕ трогаем служебную таблицу Alembic ---
def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name == "alembic_version":
        return False
    return True

# единая функция настроек, чтобы не расходились offline/online
def _configure_ctx(**kw):
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        include_object=include_object,
        # ВАЖНО: НЕ задаём version_table_schema — пусть Alembic сам создаст таблицу
        # при необходимости можно явно указать имя таблицы версий:
        version_table="alembic_version",
        **kw,
    )

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    _configure_ctx(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    _configure_ctx(connection=connection)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async def run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
