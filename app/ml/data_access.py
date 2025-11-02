from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd

from sqlalchemy import select

# сессия БД (как у тебя уже используется)
from app.db.session import async_session

# твои модели
from app.models.inventory_history import InventoryHistory
from app.models.delivery_items import DeliveryItems
from app.models.delivery import Delivery  # чтобы добраться до scheduled_at / delivered_at
from app.models.shipment import ShipmentItems  # есть связь на Shipment
from app.models.product import Product


# ===============================
# 1) История исходящих (для обучения Prophet)
#    Возвращает df с колонками ['ds','y']
#    ds — дата события (shipped_at или created_at), y — сумма fact_quantity
# ===============================
async def fetch_outgoing_timeseries(
    product_id: str,
    warehouse_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    freq: str = "D",
) -> pd.DataFrame:
    async with async_session() as session:
        stmt = select(ShipmentItems).where(ShipmentItems.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(ShipmentItems.warehouse_id == warehouse_id)
        if start:
            stmt = stmt.where(ShipmentItems.created_at >= start)
        if end:
            stmt = stmt.where(ShipmentItems.created_at <= end)
        rows = (await session.execute(stmt)).scalars().all()

    records: List[dict] = []
    for r in rows:
        # используем shipped_at родителя, иначе fallback на created_at
        ts = None
        try:
            ts = r.shipment.shipped_at if (hasattr(r, "shipment") and r.shipment and getattr(r.shipment, "shipped_at", None)) else r.created_at
        except Exception:
            ts = r.created_at
        if ts is None:
            continue
        qty = float(r.fact_quantity or 0.0)
        records.append({"ts": pd.to_datetime(ts), "y": qty})

    if not records:
        return pd.DataFrame(columns=["ds", "y"]).astype({"ds": "datetime64[ns]", "y": "float"})

    df = pd.DataFrame.from_records(records).set_index("ts").sort_index()
    # агрегируем по частоте freq
    agg = df.resample(freq).sum().fillna(0)
    agg = agg.reset_index().rename(columns={"ts": "ds"})
    # Prophet не любит tz-aware → делаем naive
    agg["ds"] = pd.to_datetime(agg["ds"]).dt.tz_localize(None)
    agg["y"] = agg["y"].astype(float)
    return agg[["ds", "y"]]


# ===============================
# 2) Снимок остатков на момент времени
#    Берём последний stock <= at_time из InventoryHistory
# ===============================
async def fetch_snapshot_at(
    product_id: str,
    warehouse_id: Optional[str],
    at_time: datetime,
) -> Optional[float]:
    async with async_session() as session:
        stmt = select(InventoryHistory).where(InventoryHistory.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(InventoryHistory.warehouse_id == warehouse_id)
        stmt = stmt.where(InventoryHistory.created_at <= at_time).order_by(InventoryHistory.created_at.desc())
        row = (await session.execute(stmt)).scalars().first()

    if not row:
        return None
    return float(row.stock) if row.stock is not None else None


# ===============================
# 3) Плановые приходы
#    Строим df ['ds','incoming'] из DeliveryItems → Delivery.scheduled_at
# ===============================
async def fetch_planned_incoming(
    product_id: str,
    warehouse_id: Optional[str],
    start: datetime,
    end: datetime,
    freq: str = "D",
) -> pd.DataFrame:
    async with async_session() as session:
        stmt = select(DeliveryItems).where(DeliveryItems.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(DeliveryItems.warehouse_id == warehouse_id)
        rows = (await session.execute(stmt)).scalars().all()

    # 👉 приведём границы к naive UTC, чтобы верно сравнивать с БДшными значениями
    start_naive = pd.to_datetime(start).tz_localize(None)
    end_naive = pd.to_datetime(end).tz_localize(None)

    records: List[dict] = []
    for item in rows:
        # план берем из Delivery.scheduled_at
        sched = None
        try:
            sched = item.delivery.scheduled_at if (hasattr(item, "delivery") and item.delivery and getattr(item.delivery, "scheduled_at", None)) else None
        except Exception:
            sched = None

        if sched is not None:
            sched_naive = pd.to_datetime(sched).tz_localize(None)  # 👈 делаем naive
            if start_naive <= sched_naive <= end_naive:
                records.append({"ts": sched_naive, "incoming": float(item.ordered_quantity or 0.0)})

    if not records:
        return pd.DataFrame(columns=["ds", "incoming"]).astype({"ds": "datetime64[ns]", "incoming": "float"})

    df = pd.DataFrame.from_records(records).set_index("ts").sort_index()
    agg = df.resample(freq).sum().fillna(0)
    agg = agg.reset_index().rename(columns={"ts": "ds"})
    agg["ds"] = pd.to_datetime(agg["ds"]).dt.tz_localize(None)
    agg["incoming"] = agg["incoming"].astype(float)
    return agg[["ds", "incoming"]]



# ===============================
# 4) Все product_id конкретного склада (для пакетных расчётов)
#    ORM — без text(), совместимо с SQLAlchemy 2.0
# ===============================
async def fetch_all_product_ids(session, warehouse_id: str) -> List[str]:
    result = await session.execute(
        select(Product.id).where(Product.warehouse_id == warehouse_id)
    )
    return list(result.scalars().all())
