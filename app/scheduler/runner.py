# app/scheduler/runner.py
from __future__ import annotations

import time
import logging
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.scheduler.config import Config
from app.scheduler.jobs import create_shipment_job
from app.scheduler.jobs.materialize_scheduled_deliveries import run as deliveries_job
from app.scheduler.jobs.predict_scheduler import run as predict_job  # добавляем новую задачу

log = logging.getLogger("scheduler.runner")


def run_once(cfg: Config) -> None:
    """Запуск единоразово (для тестов)."""
    engine = create_engine(cfg.database_url, pool_pre_ping=True, future=True)
    with Session(engine) as session:
        create_shipment_job(session, cfg)


def loop(cfg: Config) -> None:
    """Основной цикл планировщика."""
    # интервалы для разных задач
    shipments_interval = getattr(cfg, "interval_sec", 60)               # например, каждые 60 сек
    deliveries_interval = getattr(cfg, "deliveries_interval_sec", 900)  # каждые 15 минут
    predict_interval = getattr(cfg, "predict_check_interval", 3600)     # проверяем прогнозы раз в час

    log.info(
        "Старт планировщика: shipments=%s сек, deliveries=%s сек, predict-check=%s сек",
        shipments_interval, deliveries_interval, predict_interval
    )

    engine = create_engine(cfg.database_url, pool_pre_ping=True, future=True)

    # расписание следующих запусков
    next_shipments = time.monotonic()
    next_deliveries = time.monotonic()
    next_predict_check = time.monotonic()  # отдельный цикл проверки прогнозов

    while True:
        now = time.monotonic()
        try:
            with Session(engine) as session:
                # отгрузки
                if now >= next_shipments:
                    create_shipment_job(session, cfg)
                    next_shipments = now + shipments_interval

                # поставки
                if now >= next_deliveries:
                    created = deliveries_job(session, cfg)
                    if created:
                        log.info("Materialized %s scheduled deliveries.", created)
                    next_deliveries = now + deliveries_interval

            # ML-прогнозы (выполняем асинхронно, т.к. использует async_session)
            if now >= next_predict_check:
                log.info("⏳ Проверка, кому пора обновить прогнозы...")
                try:
                    asyncio.run(predict_job(cfg))
                except Exception as e:
                    log.exception("Ошибка при выполнении ML-джобы: %s", e)
                next_predict_check = now + predict_interval

        except Exception as e:
            log.exception("Ошибка выполнения задачи: %s", e)

        if cfg.run_once:
            break

        # спим до ближайшей задачи
        sleep_for = min(next_shipments, next_deliveries, next_predict_check) - time.monotonic()
        if sleep_for > 0:
            time.sleep(min(sleep_for, 1.0))
