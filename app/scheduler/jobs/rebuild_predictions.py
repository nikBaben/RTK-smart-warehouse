import asyncio
import logging
from app.db.session import async_session
from app.repositories.product_repo import ProductRepository
from app.repositories.predict_repo import PredictRepository
from app.service.predict_service import PredictService

log = logging.getLogger("scheduler.rebuild_predictions")


#Переобучение/перерасчёт прогнозов истощения по всем товарам склада.
#Вызывается каждые N часов планировщиком.
async def run(cfg=None):
    warehouse_id = getattr(cfg, "warehouse_id","WH_001") 
    horizon_days = getattr(cfg, "horizon_days")

    log.info(f"🔁 Старт обновления прогнозов по складу {warehouse_id}")

    async with async_session() as session:
        svc = PredictService(
            PredictRepository(session),
            ProductRepository(session)
        )
        try:
            result = await svc.rebuild_predictions_for_warehouse(
                warehouse_id=warehouse_id,
                horizon_days=horizon_days,
                auto_train=False
            )
            log.info(f"✅ Прогнозы обновлены: {result}")
        except Exception as e:
            log.exception(f"❌ Ошибка при пересчёте прогнозов: {e}")

    log.info(f"🏁 Завершено обновление прогнозов по складу {warehouse_id}")
