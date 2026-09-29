import os
from dataclasses import dataclass
from datetime import timezone
from sqlalchemy.engine import make_url
from backend.core.config import settings
from backend.domain.enums import ShipmentStatus


@dataclass(frozen=True)
class Config:
    database_url: str
    interval_sec: int
    deliveries_interval_sec: int
    item_qty_default: int
    shipment_name_prefix: str
    shipment_status: ShipmentStatus
    timezone: timezone
    run_once: bool
    predict_refresh_days: int 
    predict_check_interval: int 
    horizon_days: int

def load_config() -> Config:
    # Scheduler uses synchronous SQLAlchemy sessions; API uses asyncpg.
    database_url = make_url(settings.DB_URL).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
    interval_sec = 900
    deliveries_interval_sec = 1800
    predict_check_interval = 3600
    item_qty_default = 1
    shipment_name_prefix = "Auto shipment"
    status_name = os.getenv("SHIPMENT_STATUS", "scheduled")
    predict_refresh_days = 7
    horizon_days = 30
    run_once = os.getenv("SCHEDULER_RUN_ONCE", "0") == "1"
    tz = timezone.utc
    try:
        shipment_status = ShipmentStatus[status_name]
    except Exception:
        shipment_status = ShipmentStatus.scheduled

    return Config(
        database_url=database_url,
        interval_sec=interval_sec,
        deliveries_interval_sec=deliveries_interval_sec,
        item_qty_default=item_qty_default,
        shipment_name_prefix=shipment_name_prefix,
        shipment_status=shipment_status,
        timezone=tz,
        run_once=run_once,
        predict_refresh_days=predict_refresh_days,
        predict_check_interval=predict_check_interval,
        horizon_days=horizon_days,
    )

