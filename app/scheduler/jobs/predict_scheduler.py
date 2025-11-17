# app/scheduler/predict_scheduler.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.db.session import async_session as async_session_maker
from app.repositories.predict_repo import PredictRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.service.predict_service import PredictService

log = logging.getLogger("scheduler.predict_scheduler")


# Проверяет все склады: если прогноз старше N дней (или отсутствует),
# запускает ПЕРЕСЧЁТ ПРОГНОЗОВ (используя Predictor с default_model_path).
async def run(cfg=None):
    horizon_days = getattr(cfg, "horizon_days", 60)
    refresh_days = getattr(cfg, "predict_refresh_days", 7)
    default_model_path = getattr(cfg, "default_model_path", "/app/models_store/PROD_DEMO.pkl")
    refresh_interval = timedelta(days=refresh_days)

    now = datetime.now(timezone.utc)
    log.info("🔁 Проверка необходимости обновления прогнозов (интервал %s дней)", refresh_days)

    async with async_session_maker() as session:
        repo = PredictRepository(session)
        warehouse_repo = WarehouseRepository(session)

        svc = PredictService(
            predict_repo=repo,
            warehouse_repo=warehouse_repo,
            default_model_path=default_model_path,
        )

        warehouse_ids = await warehouse_repo.list_ids()
        if not warehouse_ids:
            log.warning("⚠️ Складов не найдено")
            return

        for wid in warehouse_ids:
            last_pred = await repo.get_last_prediction_time(wid)

            if last_pred is None:
                log.info("🆕 Новый склад %s → создаём первый прогноз", wid)
                await svc.rebuild_predictions_for_warehouse(
                    warehouse_id=wid,
                    horizon_days=horizon_days,
                )
                continue

            if now - last_pred >= refresh_interval:
                log.info("⏰ Склад %s: прошло %s, пересчёт прогноза...", wid, now - last_pred)
                await svc.rebuild_predictions_for_warehouse(
                    warehouse_id=wid,
                    horizon_days=horizon_days,
                )
            else:
                log.info("✅ Склад %s: прогноз свежий (%s) — пропускаем", wid, last_pred)
