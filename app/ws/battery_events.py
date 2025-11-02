from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class RobotRepoProto(Protocol):
    async def avg_battery_by_warehouse(self, warehouse_id: str) -> float: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]: ...


#Публикация события в Redis
async def publish_robot_avg_snapshot(repo: RobotRepoProto, warehouse_id: str) -> None:
    try:
        avg = await repo.avg_battery_by_warehouse(warehouse_id)
        event = {
            "type": "robot.avg_battery",
            "warehouse_id": warehouse_id,
            "avg_battery": round(float(avg or 0.0), 2),
            "ts": _now_iso(),
        }
        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, event)
    except Exception as e:
        print(f"Ошибка в publish_robot_avg_snapshot для склада {warehouse_id}: {e}")

async def publish_robot_battery_changed(repo: RobotRepoProto, robot_id: str):
    try:
        warehouse_id = await repo.get_warehouse_id_by_robot_id(robot_id)
        if not warehouse_id:
            return
        await publish_robot_avg_snapshot(repo, warehouse_id)
    except Exception as e:
        print(f"Ошибка в publish_robot_battery_changed для {robot_id}: {e}")

async def publish_robot_deleted(repo: RobotRepoProto, robot_id: str, warehouse_id: str):
    try:
        await publish_robot_avg_snapshot(repo, warehouse_id)
    except Exception as e:
        print(f"Ошибка в publish_robot_deleted для {robot_id}: {e}")

#Вспомогательное: выбор активных складов
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

#Периодический стример
async def continuous_robot_avg_streamer(
    repo_provider: Callable[[], AsyncContextManager[RobotRepoProto]],
    *,
    interval: float = 60.0,
    use_ws_rooms: bool = False,
):
    print(f"continuous_robot_avg_streamer запущен (interval={interval}s, use_ws_rooms={use_ws_rooms}).")
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_robot_avg_snapshot(repo, wid)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for wid in wh_ids:
                            await publish_robot_avg_snapshot(repo, wid)
            except Exception as inner_err:
                print(f"Ошибка внутри цикла стримера: {inner_err}")

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        print("continuous_robot_avg_streamer остановлен (CancelledError).")
    except Exception as e:
        print(f"Фатальная ошибка в continuous_robot_avg_streamer: {e}")
