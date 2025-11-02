# app/repositories/bundle.py
from __future__ import annotations
import contextlib
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

# Общая фабрика сессий приложения
from app.db.session import async_session

# Протоколы и бандл-тип
from app.repositories.protos import (
    RepoBundle,
    RobotRepositoryProto,
    RobotHistoryRepositoryProto,
    ProductRepositoryProto,
    InventoryHistoryRepositoryProto,
    WarehouseRepositoryProto,
)

# Конкретные реализации репозиториев
from app.repositories.robot_repo import RobotRepository
from app.repositories.robot_history_repo import RobotHistoryRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_history_repo import InventoryHistoryRepository
from app.repositories.warehouse_repo import WarehouseRepository


__all__ = [
    "RepoBundle",
    "repo_bundle_provider",
    "repo_bundle_provider_from_session",
    "product_repo_provider",
    "robot_history_repo_provider",
    "inventory_history_repo_provider",
    "robot_repo_provider",
    "warehouse_repo_provider",
]

# Вспомогательная фабрика для сборки бандла из конкретной AsyncSession
def _make_repo_bundle(session: AsyncSession) -> RepoBundle:
    """
    Собирает RepoBundle на одной и той же AsyncSession.
    Все репозитории разделяют единый юнит работы (транзакцию).
    """
    robot: RobotRepositoryProto = RobotRepository(session)
    robot_history: RobotHistoryRepositoryProto = RobotHistoryRepository(session)
    product: ProductRepositoryProto = ProductRepository(session)
    inv_hist: InventoryHistoryRepositoryProto = InventoryHistoryRepository(session)
    warehouse: WarehouseRepositoryProto = WarehouseRepository(session)

    return RepoBundle(
        robot=robot,
        robot_history=robot_history,
        product=product,
        inv_hist=inv_hist,
        warehouse=warehouse,
    )

# Главный провайдер бандла: сам создаёт сессию и управляет транзакцией
@asynccontextmanager
async def repo_bundle_provider(*, commit_on_exit: bool = True) -> AsyncIterator[RepoBundle]:
    async with async_session() as session:
        try:
            async with session.begin():
                bundle = _make_repo_bundle(session)
                yield bundle
            # begin() сам делает COMMIT, когда блок завершился без исключений.
            # Доп. флаг commit_on_exit оставлен для совместимости — если False,
            # мы делаем откат после .begin(), чтобы не фиксировать изменения.
            if not commit_on_exit:
                await session.rollback()
        except Exception:
            # Если исключение внутри блока .begin(), транзакция уже откатится;
            # здесь делаем дополнительный rollback на всякий случай.
            with contextlib.suppress(Exception):  # type: ignore[name-defined]
                await session.rollback()
            raise


# ──────────────────────────────────────────────────────────────────────────────
# Провайдер из внешней (уже созданной) AsyncSession — когда сессия управляется снаружи
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def repo_bundle_provider_from_session(
    session: AsyncSession,
    *,
    manage_transaction: bool = False,
) -> AsyncIterator[RepoBundle]:
    """
    Оборачивает уже созданную сессию в RepoBundle.

    manage_transaction:
        - False (по умолч.) — транзакцией управляет вызывающая сторона.
        - True  — внутри откроем session.begin(), коммит/роллбек на нашей стороне.
    """
    if not manage_transaction:
        # Без управления транзакцией: просто отдаём бандл и выходим.
        bundle = _make_repo_bundle(session)
        yield bundle
        return

    try:
        async with session.begin():
            bundle = _make_repo_bundle(session)
            yield bundle
        # session.begin() сам сделает COMMIT при успешном выполнении блока.
    except Exception:
        with contextlib.suppress(Exception):  # type: ignore[name-defined]
            await session.rollback()
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Узкие провайдеры под отдельные репозитории (удобно для ws/stream кода)
# Все провайдеры открывают единую транзакцию и коммитят на выходе.
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def product_repo_provider(*, commit_on_exit: bool = True) -> AsyncIterator[ProductRepositoryProto]:
    async with repo_bundle_provider(commit_on_exit=commit_on_exit) as repos:
        yield repos.product


@asynccontextmanager
async def robot_history_repo_provider(*, commit_on_exit: bool = True) -> AsyncIterator[RobotHistoryRepositoryProto]:
    async with repo_bundle_provider(commit_on_exit=commit_on_exit) as repos:
        yield repos.robot_history


@asynccontextmanager
async def inventory_history_repo_provider(*, commit_on_exit: bool = True) -> AsyncIterator[InventoryHistoryRepositoryProto]:
    async with repo_bundle_provider(commit_on_exit=commit_on_exit) as repos:
        yield repos.inv_hist


@asynccontextmanager
async def robot_repo_provider(*, commit_on_exit: bool = True) -> AsyncIterator[RobotRepositoryProto]:
    async with repo_bundle_provider(commit_on_exit=commit_on_exit) as repos:
        yield repos.robot


@asynccontextmanager
async def warehouse_repo_provider(*, commit_on_exit: bool = True) -> AsyncIterator[WarehouseRepositoryProto]:
    async with repo_bundle_provider(commit_on_exit=commit_on_exit) as repos:
        yield repos.warehouse
