from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Protocol, AsyncContextManager, Callable, Tuple

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:
    manager = None  # type: ignore


ACTIVE_STATUSES: Tuple[str, ...] = ("idle", "scanning")

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class RobotRepoProto(Protocol):
    async def total_robots(self, warehouse_id: str) -> int: ...
    async def counts_by_status(
        self, warehouse_id: str, only_statuses: Tuple[str, ...]
    ) -> Dict[str, int]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]: ...


#Публикации
async def publish_robot_status_count_snapshot(
    repo: RobotRepoProto,
    warehouse_id: str,
):
    total_robots = await repo.total_robots(warehouse_id)
    per_status = await repo.counts_by_status(warehouse_id, ACTIVE_STATUSES)
    active_total = sum(per_status.values())

    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "robot.active_robots",
        "warehouse_id": warehouse_id,
        "active_robots": active_total,
        "robots": total_robots,
        "per_status": per_status,
        "ts": _now_iso(),
    })


async def publish_robot_status_changed(repo: RobotRepoProto, robot_id: str) -> None:
    warehouse_id = await repo.get_warehouse_id_by_robot_id(robot_id)
    if not warehouse_id:
        return
    await publish_robot_status_count_snapshot(repo, warehouse_id)


async def publish_robot_deleted(repo: RobotRepoProto, robot_id: str, warehouse_id: str) -> None:
    await publish_robot_status_count_snapshot(repo, warehouse_id)


#Выбор активных складов
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []

async def _get_active_warehouses_by_repo(repo: RobotRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        return []


#Фоновая задача
async def continuous_robot_status_count_streamer(
    repo_provider: Callable[[], AsyncContextManager[RobotRepoProto]],
    *,
    interval: float = 5.0,
    use_ws_rooms: bool = False,
):
    print(f"continuous_robot_status_count_streamer(interval={interval}, use_ws_rooms={use_ws_rooms})")
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for warehouse_id in wh_ids:
                                await publish_robot_status_count_snapshot(repo, warehouse_id)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for warehouse_id in wh_ids:
                            await publish_robot_status_count_snapshot(repo, warehouse_id)
            except Exception as inner_err:
                print(f"continuous_robot_status_count_streamer inner error: {inner_err}")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("continuous_robot_status_count_streamer cancelled")
    except Exception as e:
        print(f"continuous_robot_status_count_streamer fatal error: {e}")
