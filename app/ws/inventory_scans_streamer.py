from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _now_iso() -> str:
    return _now_utc().isoformat()

def _cutoff_utc(hours: int = 24) -> datetime:
    return _now_utc() - timedelta(hours=hours)

class InventoryHistoryRepoProto(Protocol):
    async def count_scans_since(self, warehouse_id: str, since_utc: datetime) -> int: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...


#Паблишер в Redis
async def publish_inventory_scanned_24h_snapshot(
    repo: InventoryHistoryRepoProto,
    warehouse_id: str,
    hours: int = 24,
):
    try:
        cutoff = _cutoff_utc(hours)
        count = await repo.count_scans_since(warehouse_id, cutoff)

        event: Dict[str, Any] = {
            "type": "inventory.scanned_24h",
            "warehouse_id": warehouse_id,
            "count": int(count or 0),
            "hours": hours,
            "ts": _now_iso(),
        }

        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, event)
    except Exception as e:
        print(f"publish_inventory_scanned_24h_snapshot({warehouse_id}) error: {e}")


async def publish_inventory_new_scan(repo: InventoryHistoryRepoProto, history_id: str, hours: int = 24) -> None:
    try:
        warehouse_id: Optional[str] = await repo.get_warehouse_id_by_history_id(history_id)
        if not warehouse_id:
            return
        await publish_inventory_scanned_24h_snapshot(repo, warehouse_id, hours=hours)
    except Exception as e:
        print(f"publish_inventory_new_scan({history_id}) error: {e}")


#Способы получить список «активных» складов
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []

async def _get_active_warehouses_by_repo(repo: InventoryHistoryRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        return []


#Периодический стример
async def continuous_inventory_scans_streamer(
    repo_provider: Callable[[], AsyncContextManager[InventoryHistoryRepoProto]],
    *,
    interval: float = 30.0,
    hours: int = 24,
    use_ws_rooms: bool = False,
):
    print(f"continuous_inventory_scans_streamer(interval={interval}, hours={hours}, use_ws_rooms={use_ws_rooms})")
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_inventory_scanned_24h_snapshot(repo, wid, hours=hours)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for wid in wh_ids:
                            await publish_inventory_scanned_24h_snapshot(repo, wid, hours=hours)
            except Exception as inner_err:
                print(f"continuous_inventory_scans_streamer inner error: {inner_err}")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("continuous_inventory_scans_streamer cancelled")
    except Exception as e:
        print(f"continuous_inventory_scans_streamer fatal error: {e}")
