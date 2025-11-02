from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class InventoryHistoryRepoProto(Protocol):
    async def count_critical_unique_articles(self, warehouse_id: str) -> int: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...


#Публикация события в Redis
async def publish_critical_unique_articles_snapshot(
    repo: InventoryHistoryRepoProto,
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
    except Exception as e:
        print(f"publish_critical_unique_articles_snapshot({warehouse_id}) error: {e}")


async def publish_inventory_history_changed(repo: InventoryHistoryRepoProto, history_id: str) -> None:
    try:
        warehouse_id = await repo.get_warehouse_id_by_history_id(history_id)
        if not warehouse_id:
            return
        await publish_critical_unique_articles_snapshot(repo, warehouse_id)
    except Exception as e:
        print(f"publish_inventory_history_changed({history_id}) error: {e}")


#Вспомогательные выборки активных складов
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []

#Список складов, для которых вообще есть записи (worker-режим).
async def _get_active_warehouses_by_repo(repo: InventoryHistoryRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        return []

#Периодический стример
async def continuous_inventory_critical_streamer(
    repo_provider: Callable[[], AsyncContextManager[InventoryHistoryRepoProto]],
    *,
    interval: float = 30.0,
    use_ws_rooms: bool = False,
):
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_critical_unique_articles_snapshot(repo, wid)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for wid in wh_ids:
                            await publish_critical_unique_articles_snapshot(repo, wid)
            except Exception as inner_err:
                print(f"continuous_inventory_critical_streamer inner error: {inner_err}")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("continuous_inventory_critical_streamer cancelled")
    except Exception as e:
        print(f"continuous_inventory_critical_streamer fatal error: {e}")
