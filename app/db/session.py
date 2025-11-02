from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

POOL_SIZE = int(getattr(settings, "DB_POOL_SIZE", 300))
MAX_OVERFLOW = int(getattr(settings, "DB_MAX_OVERFLOW", 600))
POOL_TIMEOUT = float(getattr(settings, "DB_POOL_TIMEOUT", 30.0))
POOL_RECYCLE = int(getattr(settings, "DB_POOL_RECYCLE", 1800))  # 30 минут

engine = create_async_engine(
    settings.DB_URL,
    echo=False,
    future=True,
    pool_size=POOL_SIZE,          # постоянный пул
    max_overflow=MAX_OVERFLOW,    # доп. временные соединения
    pool_timeout=POOL_TIMEOUT,    # ожидание свободного соединения
    pool_recycle=POOL_RECYCLE,    # раз в N сек перезапуск соединений (anti-idle)
    pool_pre_ping=True,           # проверка соединения перед выдачей из пула
)

# sessionmaker с отключённым expire_on_commit — чтобы данные не инвалидировались после commit()
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# dependency для FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
