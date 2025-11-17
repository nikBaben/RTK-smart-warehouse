import time
import logging
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.scheduler.config import Config
from app.scheduler.jobs import create_shipment_job
from app.scheduler.jobs.materialize_scheduled_deliveries import run as deliveries_job
from app.scheduler.jobs.predict_scheduler import run as predict_job

log = logging.getLogger("scheduler.runner")


# Тестовый однократный запуск
def run_once(cfg: Config) -> None:
    engine = create_engine(cfg.database_url, pool_pre_ping=True, future=True)
    with Session(engine) as session:
        create_shipment_job(session, cfg)


def _schedule_predict_job(cfg: Config) -> None:
    """
    Безопасный запуск асинхронной ML-джобы:
    - если уже есть активный event loop → создаём задачу и НЕ блокируем.
    - если нет → запускаем отдельный цикл через asyncio.run().
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(predict_job(cfg))
    else:
        asyncio.run(predict_job(cfg))


# Планировщик задач
def loop(cfg: Config) -> None:
    shipments_interval = getattr(cfg, "interval_sec")
    deliveries_interval = getattr(cfg, "deliveries_interval_sec")
    predict_interval = getattr(cfg, "predict_check_interval")

    log.info(
        "Старт планировщика: shipments=%s сек, deliveries=%s сек, predict-check=%s сек",
        shipments_interval, deliveries_interval, predict_interval
    )

    engine = create_engine(cfg.database_url, pool_pre_ping=True, future=True)

    next_shipments = time.monotonic()
    next_deliveries = time.monotonic()
    next_predict_check = time.monotonic()

    while True:
        now_mono = time.monotonic()
        try:
            with Session(engine) as session:
                # отгрузки
                if now_mono >= next_shipments:
                    try:
                        create_shipment_job(session, cfg)
                    finally:
                        pass
                    next_shipments = now_mono + shipments_interval

                # поставки
                if now_mono >= next_deliveries:
                    created = 0
                    try:
                        created = deliveries_job(session, cfg)
                    finally:
                        pass
                    if created:
                        log.info("Materialized %s scheduled deliveries.", created)
                    next_deliveries = now_mono + deliveries_interval

            # ML-прогнозы (асинхронно)
            if now_mono >= next_predict_check:
                log.info("⏳ Проверка, кому пора обновить прогнозы...")
                try:
                    _schedule_predict_job(cfg)
                except Exception as e:
                    log.exception("Ошибка при постановке ML-джобы: %s", e)
                next_predict_check = now_mono + predict_interval

        except Exception as e:
            log.exception("Ошибка выполнения задачи: %s", e)

        if cfg.run_once:
            break

        sleep_for = min(next_shipments, next_deliveries, next_predict_check) - time.monotonic()
        if sleep_for > 0:
            time.sleep(min(sleep_for, 1.0))
