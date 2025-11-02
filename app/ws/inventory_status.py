from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Protocol, AsyncContextManager, Callable, Optional

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ProductRepoProto(Protocol):
    async def get_avg_stock_by_status(self, warehouse_id: str) -> Dict[str, float]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...


async def publish_status_avg_snapshot(repo: ProductRepoProto, warehouse_id: str) -> None:
    try:
        avgs = await repo.get_avg_stock_by_status(warehouse_id) 
        if avgs:
            top_status, max_avg = max(avgs.items(), key=lambda item: item[1])
            max_avg = round(float(max_avg or 0.0), 2)
        else:
            top_status, max_avg = None, 0.0

        payload: Dict[str, Any] = {
            "type": "inventory.status_avg",
            "warehouse_id": warehouse_id,
            "status": top_status,
            "max_avg": max_avg,
            "avgs": avgs,
            "ts": _now_iso(),
        }
        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, payload)
    except Exception as e:
        print(f"❌ publish_status_avg_snapshot({warehouse_id}) error: {e}")

#Выбор активных складов
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []

async def _get_active_warehouses_by_repo(repo: ProductRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        return []

#Периодический стример
async def continuous_inventory_status_avg_streamer(
    repo_provider: Callable[[], AsyncContextManager[ProductRepoProto]],
    *,
    interval: float = 30.0,
    use_ws_rooms: bool = False,
) -> None:
    print(f"🚀 continuous_inventory_status_avg_streamer(interval={interval}, use_ws_rooms={use_ws_rooms})")
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_status_avg_snapshot(repo, wid)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for wid in wh_ids:
                            await publish_status_avg_snapshot(repo, wid)
            except Exception as inner_err:
                print(f"❌ continuous_inventory_status_avg_streamer inner error: {inner_err}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("🛑 continuous_inventory_status_avg_streamer cancelled")
    except Exception as e:
        print(f"🔥 continuous_inventory_status_avg_streamer fatal error: {e}")
