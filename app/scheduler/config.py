import os
from dataclasses import dataclass
from datetime import timezone
from app.models.enums import ShipmentStatus


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
    default_model_path: str

def load_config() -> Config:
    database_url = os.getenv("DB_URL")
    interval_sec = 1800
    deliveries_interval_sec = 3600
    predict_check_interval = 3800
    item_qty_default = 1
    default_model_path = "/app/models_store/PROD_DEMO.pkl"
    shipment_name_prefix = "Auto shipment"
    status_name = os.getenv("SHIPMENT_STATUS", "scheduled")
    predict_refresh_days = 7
    horizon_days = 30
    run_once = False
    tz = timezone.utc
    try:
        shipment_status = ShipmentStatus[status_name]
    except Exception:
        shipment_status = ShipmentStatus.scheduled

    return Config(
        default_model_path = default_model_path,
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

