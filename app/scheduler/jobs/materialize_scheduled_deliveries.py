import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.models.delivery_items import DeliveryItems
from app.models.delivery import ScheduledDelivery, Delivery
from app.db.audit_flags import disable_inventory_audit

try:
    from app.models.enums import DeliveryStatus as _DS
except Exception:
    _DS = None

from app.scheduler.locks import advisory_lock_key, acquire_lock, release_lock


# ---------------- util ----------------
def _status_value(x):
    return getattr(x, "value", x)


def _enum_member(name_or_value):
    if _DS is None:
        return name_or_value
    try:
        return _DS[name_or_value.upper()]
    except Exception:
        pass
    try:
        return _DS(name_or_value)
    except Exception:
        return name_or_value


SCHEDULED = _enum_member("scheduled")
DELIVERED = _enum_member("delivered")


def _inc_stock_sql(session: Session, pid: str, inc: int) -> None:
    """Атомарно увеличить stock (без ORM, без autoflush)."""
    session.execute(
        text("UPDATE products SET stock = stock + :inc WHERE id = :pid"),
        {"inc": int(inc), "pid": pid},
    )


# ---------------- main job ----------------
def run(session: Session, cfg) -> int:
    """
    ВАЖНО: мы НЕ выбираем ScheduledDelivery целиком, потому что
    joined loaders из модели создают OUTER JOIN, а PostgreSQL запрещает
    FOR UPDATE на nullable стороне OUTER JOIN.

    Поэтому: сначала SELECT только id + FOR UPDATE SKIP LOCKED,
    затем session.get(id) — безопасно.
    """

    now = datetime.now(timezone.utc)

    # глобальный lock
    lock_key = advisory_lock_key("materialize_scheduled_deliveries_v3")
    if not acquire_lock(session, lock_key):
        return 0

    processed = 0

    try:
        # ---------- 1) SELECT только ID (БЕЗ JOIN) + FOR UPDATE ----------
        q_ids = (
            select(ScheduledDelivery.id)
            .where(ScheduledDelivery.status == "scheduled")
            .where(ScheduledDelivery.scheduled_at <= now)
            .order_by(ScheduledDelivery.product_id)
            .with_for_update(skip_locked=True)
        )

        ids = [row[0] for row in session.execute(q_ids).all()]

        # ---------- 2) обработка каждой поставки отдельно ----------
        for sd_id in ids:
            attempt = 0

            while True:
                attempt += 1
                try:
                    sd: ScheduledDelivery = session.get(ScheduledDelivery, sd_id)

                    if sd is None:
                        break  # кто-то удалил → пропускаем

                    if not sd.product_id or not sd.warehouse_id:
                        sd.status = "skipped"
                        session.commit()
                        break

                    deliv_id = f"{sd.id}_D"
                    item_id = f"{sd.id}_DI"

                    with session.no_autoflush:
                        d: Optional[Delivery] = session.get(Delivery, deliv_id)
                        if d is None:
                            d = Delivery(
                                id=deliv_id,
                                name=f"Delivery plan {sd.id}",
                                warehouse_id=sd.warehouse_id,
                                scheduled_at=sd.scheduled_at,
                                delivered_at=None,
                                quantity=sd.quantity,
                                status=SCHEDULED,
                                supplier=sd.supplier,
                                notes=sd.notes,
                            )
                            session.add(d)

                        di: Optional[DeliveryItems] = session.get(DeliveryItems, item_id)
                        if di is None:
                            di = DeliveryItems(
                                id=item_id,
                                delivery_id=d.id,
                                product_id=sd.product_id,
                                warehouse_id=sd.warehouse_id,
                                ordered_quantity=sd.quantity,
                                fact_quantity=0,
                            )
                            session.add(di)
                        else:
                            di.delivery_id = d.id

                        # приемка
                        if d.scheduled_at <= now and _status_value(d.status) != _status_value(DELIVERED):

                            if not di.fact_quantity:
                                di.fact_quantity = di.ordered_quantity

                            if di.fact_quantity and di.product_id:
                                with disable_inventory_audit(session, source='delivery', ref=deliv_id):
                                    _inc_stock_sql(session, di.product_id, di.fact_quantity)

                            d.delivered_at = now
                            d.status = DELIVERED

                        sd.status = "materialized"

                    session.commit()
                    processed += 1
                    break

                except OperationalError as e:
                    session.rollback()

                    if "deadlock detected" in str(e).lower() and attempt <= 5:
                        time.sleep(0.1 * attempt)
                        continue

                    raise

        return processed

    finally:
        release_lock(session, lock_key)
        try:
            session.commit()
        except Exception:
            session.rollback()
