# app/ws/products_events.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, List, Optional, Protocol, Any
from contextlib import asynccontextmanager

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.db.session import async_session
from app.repositories.product_repo import ProductRepository
from app.repositories.protos import ProductRepositoryProto

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore

logger = logging.getLogger(__name__)

__all__ = [
    "publish_product_snapshot",
    "publish_product_change",
    "publish_product_deleted",
    "continuous_product_snapshot_streamer",
    "default_product_repo_provider",
]


# --- Протокол (узкий) для этого модуля ----------------------------------------
class ProductEventsRepoProto(Protocol):
    async def get_all_by_warehouse_id_light(self, warehouse_id: str) -> List[Any]: ...
    async def get(self, id: str) -> Optional[Any]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def recompute_statuses_for_warehouse(self, warehouse_id: str) -> int: ...


RepoForProducts = ProductRepositoryProto  # duck typing


# --- Провайдер без session.begin(), «голая» сессия -----------------------------
@asynccontextmanager
async def default_product_repo_provider() -> AsyncContextManager[RepoForProducts]:
    async with async_session() as session:
        # ВАЖНО: без session.begin(); репозиторий сам коммитит там, где нужно.
        yield ProductRepository(session)


# --- Утилиты -------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pack_product(p: Any) -> dict:
    created_at = getattr(p, "last_scanned_at", None)
    shelf_value = getattr(p, "current_shelf", None)

    # Буква полки → число (A=1, B=2, ...), иначе пытаемся int, иначе 0
    if isinstance(shelf_value, str) and len(shelf_value) == 1 and shelf_value.isalpha():
        current_shelf = ord(shelf_value.upper()) - ord("A") + 1
    else:
        try:
            current_shelf = int(shelf_value)
        except (TypeError, ValueError):
            current_shelf = 0

    return {
        "id": getattr(p, "id", None),
        "name": getattr(p, "name", None),
        "category": getattr(p, "category", None),
        "warehouse_id": getattr(p, "warehouse_id", None),
        "current_zone": getattr(p, "current_zone", None),
        "status": getattr(p, "status", None),
        "current_row": getattr(p, "current_row", 0),
        "current_shelf": current_shelf,
        "stock": getattr(p, "stock", None),
        "min_stock": getattr(p, "min_stock", None),
        "optimal_stock": getattr(p, "optimal_stock", None),
        "created_at": created_at.isoformat() if created_at else None,
    }


# --- Публикации ----------------------------------------------------------------
async def publish_product_snapshot(
    repo: ProductEventsRepoProto,
    warehouse_id: str,
    *,
    recompute_before_publish: bool = True,
) -> None:
    """
    Публикует snapshot товаров для склада.
    Пересчёт статусов выполняется в ОТДЕЛЬНОЙ, краткоживущей сессии,
    чтобы не конфликтовать с долгоживущими сессиями (например, в WS).
    """
    try:
        if recompute_before_publish:
            try:
                async with async_session() as s:
                    tmp_repo = ProductRepository(s)
                    changed = await tmp_repo.recompute_statuses_for_warehouse(warehouse_id)
                    if changed:
                        logger.debug("Recomputed %d statuses for %s", changed, warehouse_id)
            except Exception:
                # Пересчёт — best effort: не блокируем публикацию
                logger.exception("Status recompute failed for %s", warehouse_id)

        # Чтение — через переданный repo/сессию
        items_raw = await repo.get_all_by_warehouse_id_light(warehouse_id)
        items = [_pack_product(p) for p in items_raw]

        bus = await get_bus_for_current_loop()
        await bus.publish(
            COMMON_CH,
            {
                "type": "product.snapshot",
                "warehouse_id": warehouse_id,
                "items": items,
                "ts": _now_iso(),
            },
        )
    except Exception:
        logger.exception("publish_product_snapshot(%s) error", warehouse_id)


async def publish_product_change(repo: ProductEventsRepoProto, product_id: str) -> None:
    """Публикует изменение одного товара."""
    try:
        p = await repo.get(product_id)
        if not p:
            return
        bus = await get_bus_for_current_loop()
        await bus.publish(
            COMMON_CH,
            {
                "type": "product.changed",
                "warehouse_id": getattr(p, "warehouse_id", None),
                "item": _pack_product(p),
                "ts": _now_iso(),
            },
        )
    except Exception:
        logger.exception("publish_product_change(%s) error", product_id)


async def publish_product_deleted(product_id: str, warehouse_id: str) -> None:
    """Публикует удаление товара (репозиторий не нужен)."""
    try:
        bus = await get_bus_for_current_loop()
        await bus.publish(
            COMMON_CH,
            {
                "type": "product.deleted",
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "ts": _now_iso(),
            },
        )
    except Exception:
        logger.exception("publish_product_deleted(%s, %s) error", product_id, warehouse_id)


# --- Выбор активных складов ----------------------------------------------------
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        logger.exception("WS rooms fetch error")
        return []


async def _get_active_warehouses_by_repo(repo: ProductEventsRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        logger.exception("Repo distinct warehouses fetch error")
        return []


# --- Периодический стример -----------------------------------------------------
async def continuous_product_snapshot_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForProducts]] = default_product_repo_provider,
    *,
    interval: float = 10.0,
    use_ws_rooms: bool = True,
    recompute_before_publish: bool = True,
) -> None:
    """
    Каждые `interval` секунд публикует актуальный snapshot товаров.
    use_ws_rooms=True  → брать только активные WS-комнаты (API-процесс).
    use_ws_rooms=False → брать склады из репозитория (worker-процесс).
    """
    logger.info(
        "continuous_product_snapshot_streamer started (interval=%.2fs, use_ws_rooms=%s)",
        interval,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    events_repo: ProductEventsRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_product_snapshot(
                                    repo, wid, recompute_before_publish=recompute_before_publish  # type: ignore[arg-type]
                                )
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_product_snapshot(
                                repo, wid, recompute_before_publish=recompute_before_publish  # type: ignore[arg-type]
                            )
            except Exception:
                logger.exception("continuous_product_snapshot_streamer inner error")

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("continuous_product_snapshot_streamer cancelled")
        raise
    except Exception:
        logger.exception("continuous_product_snapshot_streamer fatal error")
