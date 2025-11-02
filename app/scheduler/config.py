# app/scheduler/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timezone
from app.models.enums import ShipmentStatus


@dataclass(frozen=True)
class Config:
    # ---- только одно поле без дефолта — первым ----
    database_url: str

    # ---- все остальные с безопасными дефолтами ----
    interval_sec: int = 60                          # интервал шипментов (сек)
    deliveries_interval_sec: int = 900              # интервал материализации поставок (сек) = 15 мин
    item_qty_default: int = 1                       # кол-во по умолчанию в item
    shipment_name_prefix: str = "Auto shipment"     # префикс имени шипмента
    shipment_status: ShipmentStatus = ShipmentStatus.scheduled
    timezone: timezone = timezone.utc
    run_once: bool = False
    predict_refresh_days: int = int(os.getenv("SCHEDULER_PREDICT_REFRESH_DAYS", "7"))
    predict_check_interval: int = int(os.getenv("SCHEDULER_PREDICT_CHECK_INTERVAL", "60"))


def load_config() -> Config:
    # БД
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/myapp",
    )

    # интервалы
    interval_sec = int(os.getenv("SCHEDULER_SHIPMENTS_INTERVAL", os.getenv("SCHEDULER_INTERVAL_SEC", "60")))
    deliveries_interval_sec = int(os.getenv("SCHEDULER_DELIVERIES_INTERVAL", "900"))  # 15 минут

    # параметры шипментов
    item_qty_default = int(os.getenv("SHIPMENT_ITEM_QTY", "1"))
    shipment_name_prefix = os.getenv("SHIPMENT_NAME_PREFIX", "Auto shipment")
    status_name = os.getenv("SHIPMENT_STATUS", "scheduled")

    try:
        shipment_status = ShipmentStatus[status_name]
    except Exception:
        shipment_status = ShipmentStatus.scheduled

    run_once = os.getenv("RUN_ONCE", "0") == "1"

    # можно заменить на локальную TZ, если нужно
    tz = timezone.utc

    return Config(
        database_url=database_url,
        interval_sec=interval_sec,
        deliveries_interval_sec=deliveries_interval_sec,
        item_qty_default=item_qty_default,
        shipment_name_prefix=shipment_name_prefix,
        shipment_status=shipment_status,
        timezone=tz,
        run_once=run_once,
    )

