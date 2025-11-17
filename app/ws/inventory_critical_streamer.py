from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, Dict, List, Optional, Protocol, Any

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.protos import InventoryHistoryRepositoryProto
from app.repositories.bundle import inventory_history_repo_provider

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore

__all__ = [
    "publish_critical_unique_articles_snapshot",
    "publish_inventory_history_changed",
    "continuous_inventory_critical_streamer",
    "default_inventory_history_repo_provider",
]

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Локальный протокол только для нужд этого модуля.
class InventoryCriticalRepoProto(Protocol):
    async def count_critical_unique_articles(self, warehouse_id: str) -> int: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...


# Тип, который возвращает провайдер (для читаемости):
RepoForCritical = InventoryHistoryRepositoryProto  # duck typing дорасширяет методы


def default_inventory_history_repo_provider() -> AsyncContextManager[RepoForCritical]:
    """
    Провайдер на базе твоего inventory_history_repo_provider.
    commit_on_exit=False — читаем в рамках одной транзакции и не коммитим.
    """
    return inventory_history_repo_provider(commit_on_exit=False)


# --- Публикация событий --------------------------------------------------------
async def publish_critical_unique_articles_snapshot(
    repo: InventoryCriticalRepoProto,
    warehouse_id: str,
) -> None:
    try:
        count = await repo.count_critical_unique_articles(warehouse_id)
        event: Dict[str, Any] = {
            "type": "inventory.critical_unique",
            "warehouse_id": warehouse_id,
            "unique_articles": int(count or 0),
            "ts": _now_iso(),
        }
        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, event)
    except Exception:  # pragma: no cover
        logger.exception(
            "publish_critical_unique_articles_snapshot(%s) error", warehouse_id
        )


async def publish_inventory_history_changed(
    repo: InventoryCriticalRepoProto, history_id: str
) -> None:
    try:
        warehouse_id = await repo.get_warehouse_id_by_history_id(history_id)
        if not warehouse_id:
            return
        await publish_critical_unique_articles_snapshot(repo, warehouse_id)
    except Exception:  # pragma: no cover
        logger.exception("publish_inventory_history_changed(%s) error", history_id)


# --- Вспомогательные выборки активных складов ---------------------------------
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:  # pragma: no cover
        logger.exception("WS rooms fetch error")
        return []


async def _get_active_warehouses_by_repo(repo: InventoryCriticalRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:  # pragma: no cover
        logger.exception("Repo warehouses fetch error")
        return []


# --- Периодический стример -----------------------------------------------------
async def continuous_inventory_critical_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForCritical]] = default_inventory_history_repo_provider,
    *,
    interval: float = 5.0,
    use_ws_rooms: bool = False,
) -> None:
    """
    Периодически публикует 'inventory.critical_unique' по активным складам.

    :param repo_provider: фабрика async context manager'а, отдающая репозиторий
                          (обычно default_inventory_history_repo_provider).
    :param interval: период в секундах между итерациями.
    :param use_ws_rooms: если True — берём идентификаторы складов из WS-менеджера,
                         иначе — из репозитория (фолбэк для воркера).
    """
    logger.info(
        "continuous_inventory_critical_streamer started (interval=%.2fs, use_ws_rooms=%s)",
        interval,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    critical_repo: InventoryCriticalRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_critical_unique_articles_snapshot(repo, wid)  # type: ignore[arg-type]
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_critical_unique_articles_snapshot(repo, wid)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover
                logger.exception("continuous_inventory_critical_streamer inner error")

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("continuous_inventory_critical_streamer cancelled")
        raise
    except Exception:  # pragma: no cover
        logger.exception("continuous_inventory_critical_streamer fatal error")
