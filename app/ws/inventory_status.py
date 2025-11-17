from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, Dict, List, Optional, Protocol, Any

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.protos import ProductRepositoryProto
from app.repositories.bundle import product_repo_provider

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore

__all__ = [
    "publish_status_avg_snapshot",
    "continuous_inventory_status_avg_streamer",
    "default_product_repo_provider",
]

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Локальный протокол — только то, что нужно этому модулю
class ProductStatusAvgRepoProto(Protocol):
    async def get_avg_stock_by_status(self, warehouse_id: str) -> Dict[str, float]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...


# Тип для читаемости (реальный репозиторий проходит по duck typing)
RepoForStatusAvg = ProductRepositoryProto


def default_product_repo_provider() -> AsyncContextManager[RepoForStatusAvg]:
    """
    Провайдер на базе product_repo_provider.
    commit_on_exit=False — читаем в одной транзакции и не коммитим.
    """
    return product_repo_provider(commit_on_exit=False)


# --- Публикация снэпшота -------------------------------------------------------
async def publish_status_avg_snapshot(repo: ProductStatusAvgRepoProto, warehouse_id: str) -> None:
    try:
        avgs = await repo.get_avg_stock_by_status(warehouse_id)

        if avgs:
            # Выбираем статус с максимальным средним значением
            top_status, max_avg = max(avgs.items(), key=lambda item: item[1])
            max_avg = round(float(max_avg or 0.0), 2)
        else:
            top_status, max_avg = None, 0.0

        # (Опционально) округлим значения в avgs для компактности и стабильности фронта
        rounded_avgs = {k: round(float(v or 0.0), 2) for k, v in (avgs or {}).items()}

        payload: Dict[str, Any] = {
            "type": "inventory.status_avg",
            "warehouse_id": warehouse_id,
            "status": top_status,
            "max_avg": max_avg,
            "avgs": rounded_avgs,
            "ts": _now_iso(),
        }

        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, payload)
    except Exception:  # pragma: no cover
        logger.exception("publish_status_avg_snapshot(%s) error", warehouse_id)


# --- Выбор активных складов ----------------------------------------------------
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:  # pragma: no cover
        logger.exception("WS rooms fetch error")
        return []


async def _get_active_warehouses_by_repo(repo: ProductStatusAvgRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:  # pragma: no cover
        logger.exception("Repo warehouses fetch error")
        return []


# --- Периодический стример -----------------------------------------------------
async def continuous_inventory_status_avg_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForStatusAvg]] = default_product_repo_provider,
    *,
    interval: float = 5.0,
    use_ws_rooms: bool = False,
) -> None:
    """
    Периодически публикует событие 'inventory.status_avg' по активным складам.
    :param repo_provider: фабрика async context manager'а, отдающая репозиторий
                          (обычно default_product_repo_provider).
    :param interval: период в секундах между итерациями.
    :param use_ws_rooms: если True — брать warehouse_id из WS-менеджера, иначе — из репозитория.
    """
    logger.info(
        "continuous_inventory_status_avg_streamer started (interval=%.2fs, use_ws_rooms=%s)",
        interval,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    status_repo: ProductStatusAvgRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_status_avg_snapshot(repo)  # type: ignore[arg-type]
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_status_avg_snapshot(repo, wid)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover
                logger.exception("continuous_inventory_status_avg_streamer inner error")

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("continuous_inventory_status_avg_streamer cancelled")
        raise
    except Exception:  # pragma: no cover
        logger.exception("continuous_inventory_status_avg_streamer fatal error")
