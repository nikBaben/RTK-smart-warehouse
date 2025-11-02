# app/ws/products_events.py
from __future__ import annotations
from typing import Optional, List

import asyncio
from sqlalchemy import select, distinct, text

# ✅ фабрика bus под текущий event loop
from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.db.session import async_session
from app.models.product import Product

# Менеджер комнат (есть только в API-процессе)
try:
    from app.ws.ws_manager import manager
except Exception:
    manager = None  # type: ignore


# ---------- packing ----------
def _pack_product(p: Product) -> dict:
    created_at = getattr(p, "last_scanned_at", None)
    shelf_value = getattr(p, "current_shelf", None)

    # 🔤 Преобразуем возможную букву в номер по алфавиту
    if isinstance(shelf_value, str) and len(shelf_value) == 1 and shelf_value.isalpha():
        current_shelf = ord(shelf_value.upper()) - ord("A") + 1
    else:
        try:
            current_shelf = int(shelf_value)
        except (TypeError, ValueError):
            current_shelf = 0

    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "warehouse_id": p.warehouse_id,
        "current_zone": getattr(p, "current_zone", None),
        "status": getattr(p, "status", None),
        "current_row": getattr(p, "current_row", 0),
        "current_shelf": current_shelf,  # ✅ всегда число
        "stock": getattr(p, "stock", None),
        "min_stock": getattr(p, "min_stock", None),
        "optimal_stock": getattr(p, "optimal_stock", None),
        "created_at": created_at.isoformat() if created_at else None,
    }


# ---------- внутренние БД-хелперы ----------
async def _get_products_by_warehouse_id(warehouse_id: str) -> List[Product]:
    try:
        async with async_session() as session:
            rows = await session.execute(
                select(Product).where(Product.warehouse_id == warehouse_id)
            )
            return list(rows.scalars().all())
    except Exception as e:
        print(f"❌ _get_products_by_warehouse_id({warehouse_id}) error: {e}")
        return []


async def _get_product(product_id: str) -> Optional[Product]:
    try:
        async with async_session() as session:
            row = await session.execute(select(Product).where(Product.id == product_id))
            return row.scalar_one_or_none()
    except Exception as e:
        print(f"❌ _get_product({product_id}) error: {e}")
        return None


async def _get_distinct_warehouse_ids() -> List[str]:
    try:
        async with async_session() as session:
            rows = await session.execute(select(distinct(Product.warehouse_id)))
            return [wid for (wid,) in rows.all() if wid]
    except Exception as e:
        print(f"❌ _get_distinct_warehouse_ids error: {e}")
        return []


async def _recompute_statuses_for_warehouse(warehouse_id: str) -> None:
    """
    Опциональный пересчёт статусов перед публикацией снапшота.
    Вызываем SELECT recompute_product_statuses(uuid) только если такая функция существует.
    Любые ошибки не блокируют публикацию snapshot.
    """
    try:
        async with async_session() as session:
            # Проверяем наличие функции с нужной сигнатурой (uuid) в текущем search_path
            exists = (
                await session.execute(
                    text("SELECT to_regprocedure('recompute_product_statuses(uuid)') IS NOT NULL")
                )
            ).scalar()
            if not exists:
                return  # функции нет — тихо выходим

            try:
                await session.execute(
                    text("SELECT recompute_product_statuses(:wid::uuid)"),
                    {"wid": warehouse_id},
                )
                await session.commit()
            except Exception as call_err:
                await session.rollback()
                # не критично — просто сообщим и продолжим
                print(f"⚠️ recompute statuses failed for {warehouse_id}: {call_err}")
    except Exception as e:
        print(f"❌ _recompute_statuses_for_warehouse({warehouse_id}) error: {e}")


# ---------- публикации ----------
async def publish_product_snapshot(warehouse_id: str) -> None:
    # попытка пересчитать статусы (если функция есть)
    await _recompute_statuses_for_warehouse(warehouse_id)

    items_raw = await _get_products_by_warehouse_id(warehouse_id)
    items = [_pack_product(p) for p in items_raw]

    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.snapshot",
        "warehouse_id": warehouse_id,
        "items": items,
    })


async def publish_product_change(product_id: str) -> None:
    p = await _get_product(product_id)
    if not p:
        return
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.changed",
        "warehouse_id": p.warehouse_id,
        "item": _pack_product(p),
    })


async def publish_product_deleted(product_id: str, warehouse_id: str) -> None:
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, {
        "type": "product.deleted",
        "warehouse_id": warehouse_id,
        "product_id": product_id,
    })


# ---------- выбор активных складов ----------
async def _get_active_warehouses_by_ws() -> List[str]:
    """Список складов с активными WS-подписчиками (API-режим)."""
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []


async def _get_active_warehouses_by_db() -> List[str]:
    """Список складов, по которым есть товары (worker-режим)."""
    return await _get_distinct_warehouse_ids()


# ---------- периодический стример ----------
async def continuous_product_snapshot_streamer(
    *,
    interval: float = 60.0,
    use_ws_rooms: bool = True,
) -> None:
    """
    Каждые `interval` секунд публикует актуальный snapshot товаров.
    use_ws_rooms=True  → брать только комнаты с активными WS-подписчиками (API-процесс).
    use_ws_rooms=False → брать склады из БД (worker-процесс).
    """
    print(f"🚀 continuous_product_snapshot_streamer(interval={interval}, use_ws_rooms={use_ws_rooms})")
    try:
        while True:
            try:
                if use_ws_rooms:
                    wh_ids = await _get_active_warehouses_by_ws()
                    if wh_ids:
                        for warehouse_id in wh_ids:
                            await publish_product_snapshot(warehouse_id)
                else:
                    wh_ids = await _get_active_warehouses_by_db()
                    for warehouse_id in wh_ids:
                        await publish_product_snapshot(warehouse_id)
            except Exception as inner_err:
                print(f"❌ continuous_product_snapshot_streamer inner error: {inner_err}")

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("🛑 continuous_product_snapshot_streamer cancelled")
    except Exception as e:
        print(f"🔥 continuous_product_snapshot_streamer fatal error: {e}")
