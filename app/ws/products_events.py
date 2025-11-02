from __future__ import annotations
from typing import Optional, List, Protocol, Awaitable, Callable, Any,AsyncContextManager
import asyncio
from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


class ProductRepoProto(Protocol):
    async def get_all_by_warehouse_id(self, warehosue_id: str) -> list[Any]: ...
    async def get(self, id: str) -> Optional[Any]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def recompute_statuses_for_warehouse(self, warehouse_id: str) -> int: ...


def _pack_product(p: Any) -> dict:
    created_at = getattr(p, "last_scanned_at", None)
    shelf_value = getattr(p, "current_shelf", None)

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

#публикации
async def publish_product_snapshot(repo: ProductRepoProto, warehouse_id: str):
    items_raw = await repo.get_all_by_warehouse_id(warehouse_id)
    items = [_pack_product(p) for p in items_raw]
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.snapshot",
        "warehouse_id": warehouse_id,
        "items": items,
    })


async def publish_product_change(repo: ProductRepoProto, product_id: str):
    p = await repo.get(product_id)
    if not p:
        return
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.changed",
        "warehouse_id": getattr(p, "warehouse_id", None),
        "item": _pack_product(p),
    })


async def publish_product_snapshot(repo: ProductRepoProto, warehouse_id: str):
    try:
        await repo.recompute_statuses_for_warehouse(warehouse_id)
    except Exception as e:
        print(f"⚠️ failed to recompute statuses for {warehouse_id}: {e}")

    items_raw = await repo.get_all_by_warehouse_id(warehouse_id)
    items = [_pack_product(p) for p in items_raw]
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.snapshot",
        "warehouse_id": warehouse_id,
        "items": items,
    })


#выбор активных складов
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


#Cтример
async def continuous_product_snapshot_streamer(
    repo_provider: Callable[[], AsyncContextManager[ProductRepoProto]],
    *,
    interval: float = 60,
    use_ws_rooms: bool = True,
):
    print(f"continuous_product_snapshot_streamer(interval={interval}, use_ws_rooms={use_ws_rooms})")
    try:
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for warehouse_id in wh_ids:
                                await publish_product_snapshot(repo, warehouse_id)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for warehouse_id in wh_ids:
                            await publish_product_snapshot(repo, warehouse_id)
            except Exception as inner_err:
                print(f"continuous_product_snapshot_streamer inner error: {inner_err}")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("continuous_product_snapshot_streamer cancelled")
    except Exception as e:
        print(f"continuous_product_snapshot_streamer fatal error: {e}")
