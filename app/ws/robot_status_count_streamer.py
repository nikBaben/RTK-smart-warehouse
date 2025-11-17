from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, Dict, List, Optional, Protocol, Tuple

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.bundle import robot_repo_provider
from app.repositories.protos import RobotRepositoryProto

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore

logger = logging.getLogger(__name__)

__all__ = [
    "publish_robot_status_count_snapshot",
    "publish_robot_status_changed",
    "publish_robot_deleted",
    "continuous_robot_status_count_streamer",
    "default_robot_repo_provider",
]

ACTIVE_STATUSES: Tuple[str, ...] = ("idle", "scanning")


# --- Локальный протокол: только нужные методы ---------------------------------
class RobotStatusRepoProto(Protocol):
    async def total_robots(self, warehouse_id: str) -> int: ...
    async def counts_by_status(self, warehouse_id: str, only_statuses: Tuple[str, ...]) -> Dict[str, int]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]: ...


RepoForStatus = RobotRepositoryProto  # duck typing


def default_robot_repo_provider() -> AsyncContextManager[RepoForStatus]:
    """Провайдер на базе robot_repo_provider; commit_on_exit=False — только чтение."""
    return robot_repo_provider(commit_on_exit=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Публикации ----------------------------------------------------------------
async def publish_robot_status_count_snapshot(repo: RobotStatusRepoProto, warehouse_id: str) -> None:
    try:
        total_robots = await repo.total_robots(warehouse_id)
        per_status = await repo.counts_by_status(warehouse_id, ACTIVE_STATUSES)
        # гарантируем, что ключи есть, даже если БД вернула пусто
        per_status = {k: int(per_status.get(k, 0)) for k in ACTIVE_STATUSES}
        active_total = sum(per_status.values())

        bus = await get_bus_for_current_loop()
        await bus.publish(
            COMMON_CH,
            {
                "type": "robot.active_robots",
                "warehouse_id": warehouse_id,
                "active_robots": active_total,
                "robots": int(total_robots or 0),
                "per_status": per_status,
                "ts": _now_iso(),
            },
        )
    except Exception:  # pragma: no cover
        logger.exception("publish_robot_status_count_snapshot(%s) error", warehouse_id)


async def publish_robot_status_changed(repo: RobotStatusRepoProto, robot_id: str) -> None:
    try:
        warehouse_id = await repo.get_warehouse_id_by_robot_id(robot_id)
        if not warehouse_id:
            return
        await publish_robot_status_count_snapshot(repo, warehouse_id)
    except Exception:  # pragma: no cover
        logger.exception("publish_robot_status_changed(%s) error", robot_id)


async def publish_robot_deleted(repo: RobotStatusRepoProto, robot_id: str, warehouse_id: str) -> None:
    try:
        await publish_robot_status_count_snapshot(repo, warehouse_id)
    except Exception:  # pragma: no cover
        logger.exception("publish_robot_deleted(%s, %s) error", robot_id, warehouse_id)


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


async def _get_active_warehouses_by_repo(repo: RobotStatusRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:  # pragma: no cover
        logger.exception("Repo distinct warehouses fetch error")
        return []


# --- Фоновая задача ------------------------------------------------------------
async def continuous_robot_status_count_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForStatus]] = default_robot_repo_provider,
    *,
    interval: float = 5.0,
    use_ws_rooms: bool = False,
) -> None:
    """
    Периодически публикует счётчики активных роботов по складам.
    """
    logger.info(
        "continuous_robot_status_count_streamer started (interval=%.2fs, use_ws_rooms=%s)",
        interval,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    status_repo: RobotStatusRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_robot_status_count_snapshot(repo, wid)  # type: ignore[arg-type]
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_robot_status_count_snapshot(repo, wid)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover
                logger.exception("continuous_robot_status_count_streamer inner error")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("continuous_robot_status_count_streamer cancelled")
        raise
    except Exception:  # pragma: no cover
        logger.exception("continuous_robot_status_count_streamer fatal error")
