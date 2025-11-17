from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncContextManager, Callable, Dict, List, Optional, Protocol, Any

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.protos import InventoryHistoryRepositoryProto
from app.repositories.bundle import inventory_history_repo_provider

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore

__all__ = [
    "publish_inventory_scanned_24h_snapshot",
    "publish_inventory_new_scan",
    "continuous_inventory_scans_streamer",
    "default_inventory_history_repo_provider",
]

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _cutoff_utc(hours: int = 24) -> datetime:
    return _now_utc() - timedelta(hours=hours)


# Локальный протокол — только необходимые этому модулю методы
class InventoryScansRepoProto(Protocol):
    async def count_scans_since(self, warehouse_id: str, since_utc: datetime) -> int: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...


# Тип для читаемости (duck typing расширит методы)
RepoForScans = InventoryHistoryRepositoryProto


def default_inventory_history_repo_provider() -> AsyncContextManager[RepoForScans]:
    """
    Провайдер на базе твоего inventory_history_repo_provider.
    commit_on_exit=False — читаем в одной транзакции и не коммитим.
    """
    return inventory_history_repo_provider(commit_on_exit=False)


# --- Публикация событий --------------------------------------------------------
async def publish_inventory_scanned_24h_snapshot(
    repo: InventoryScansRepoProto,
    warehouse_id: str,
    hours: int = 24,
) -> None:
    try:
        cutoff = _cutoff_utc(hours)
        count = await repo.count_scans_since(warehouse_id, cutoff)

        event: Dict[str, Any] = {
            "type": "inventory.scanned_24h",  # сохраняем совместимость с названием события
            "warehouse_id": warehouse_id,
            "count": int(count or 0),
            "hours": hours,
            "ts": _now_iso(),
        }

        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, event)
    except Exception:  # pragma: no cover
        logger.exception("publish_inventory_scanned_24h_snapshot(%s) error", warehouse_id)


async def publish_inventory_new_scan(
    repo: InventoryScansRepoProto,
    history_id: str,
    hours: int = 24,
) -> None:
    try:
        warehouse_id: Optional[str] = await repo.get_warehouse_id_by_history_id(history_id)
        if not warehouse_id:
            return
        await publish_inventory_scanned_24h_snapshot(repo, warehouse_id, hours=hours)
    except Exception:  # pragma: no cover
        logger.exception("publish_inventory_new_scan(%s) error", history_id)


# --- Способы получить список «активных» складов --------------------------------
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:  # pragma: no cover
        logger.exception("WS rooms fetch error")
        return []


async def _get_active_warehouses_by_repo(repo: InventoryScansRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:  # pragma: no cover
        logger.exception("Repo warehouses fetch error")
        return []


# --- Периодический стример -----------------------------------------------------
async def continuous_inventory_scans_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForScans]] = default_inventory_history_repo_provider,
    *,
    interval: float = 5.0,
    hours: int = 24,
    use_ws_rooms: bool = False,
) -> None:
    """
    Периодически публикует событие 'inventory.scanned_24h' по активным складам.
    :param repo_provider: фабрика async context manager'а, отдающая репозиторий
                          (обычно default_inventory_history_repo_provider).
    :param interval: период в секундах между итерациями.
    :param hours: размер окна в часах (по умолчанию 24).
    :param use_ws_rooms: если True — брать warehouse_id из WS-менеджера, иначе — из репозитория.
    """
    logger.info(
        "continuous_inventory_scans_streamer started (interval=%.2fs, hours=%d, use_ws_rooms=%s)",
        interval,
        hours,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    scans_repo: InventoryScansRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_inventory_scanned_24h_snapshot(repo, wid, hours=hours)  # type: ignore[arg-type]
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_inventory_scanned_24h_snapshot(repo, wid, hours=hours)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover
                logger.exception("continuous_inventory_scans_streamer inner error")

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("continuous_inventory_scans_streamer cancelled")
        raise
    except Exception:  # pragma: no cover
        logger.exception("continuous_inventory_scans_streamer fatal error")
