# app/scheduler/jobs/materialize_scheduled_deliveries.py
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.delivery import Delivery, ScheduledDelivery
from app.models.delivery_items import DeliveryItems

HORIZON_HOURS = 24  # как далеко вперёд разворачивать планы

def run(session: Session, cfg) -> int:
    now = datetime.utcnow()
    horizon = now + timedelta(hours=HORIZON_HOURS)

    rows = session.execute(
        select(ScheduledDelivery)
        .where(ScheduledDelivery.status == "scheduled")
        .where(ScheduledDelivery.scheduled_at <= horizon)
    ).scalars().all()

    created = 0
    for sd in rows:
        if not sd.product_id or not sd.warehouse_id or not sd.scheduled_at:
            continue

        deliv_id = f"{sd.id}_D"
        item_id = f"{sd.id}_DI"

        # идемпотентность: пропустим, если уже есть
        if session.get(Delivery, deliv_id) is None:
            d = Delivery(
                id=deliv_id,
                name=f"Delivery plan {sd.id}",
                warehouse_id=sd.warehouse_id,
                scheduled_at=sd.scheduled_at,
                delivered_at=None,
                quantity=sd.quantity,
                status="scheduled",
            )
            di = DeliveryItems(
                id=item_id,
                delivery_id=deliv_id,
                product_id=sd.product_id,
                warehouse_id=sd.warehouse_id,
                ordered_quantity=sd.quantity,
                fact_quantity=0,
            )
            session.add(d)
            session.add(di)
            created += 1

        # пометим план как материализованный (можно не помечать — на твой вкус)
        sd.status = "materialized"

    session.commit()
    return created
