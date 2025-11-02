import logging
from datetime import datetime, timedelta, timezone
from app.db.session import async_session as async_session_maker
from app.repositories.predict_repo import PredictRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.service.predict_service import PredictService

log = logging.getLogger("scheduler.predict_scheduler")

async def run(cfg=None):
    """
    Проверяет все склады: если прогноз старше 7 дней (или отсутствует),
    запускает перерасчёт.
    """
    horizon_days = getattr(cfg, "horizon_days", 60)
    refresh_days = getattr(cfg, "predict_refresh_days", 7)
    refresh_interval = timedelta(days=refresh_days)

    now = datetime.now(timezone.utc)
    log.info(f"🔁 Проверка необходимости обновления прогнозов (интервал {refresh_days} дней)")

    async with async_session_maker() as session:
        repo = PredictRepository(session)
        svc = PredictService(repo)
        warehouse_repo = WarehouseRepository(session)

        warehouse_ids = await warehouse_repo.list_ids()
        if not warehouse_ids:
            log.warning("⚠️ Складов не найдено")
            return

        for wid in warehouse_ids:
            last_pred = await repo.get_last_prediction_time(wid)

            if last_pred is None:
                log.info(f"🆕 Новый склад {wid} → создаём первый прогноз")
                await svc.rebuild_predictions_for_warehouse(wid, horizon_days)
                continue

            if now - last_pred >= refresh_interval:
                log.info(f"⏰ Склад {wid}: прошло {now - last_pred}, пересчёт прогноза...")
                await svc.rebuild_predictions_for_warehouse(wid, horizon_days)
            else:
                log.info(f"✅ Склад {wid}: прогноз свежий ({last_pred}) — пропускаем")
