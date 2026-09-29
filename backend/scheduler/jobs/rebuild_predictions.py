from backend.repositories.warehouse_repo import WarehouseRepository
from backend.db.transaction import SqlAlchemyTransaction
from backend.ml.predictor import Predictor
import asyncio
import logging
from backend.db.session import async_session
from backend.repositories.product_repo import ProductRepository
from backend.repositories.predict_repo import PredictRepository
from backend.service.predict_service import PredictService

log = logging.getLogger("scheduler.rebuild_predictions")


#Переобучение/перерасчёт прогнозов истощения по всем товарам склада.
#Вызывается каждые N часов планировщиком.
async def run(cfg=None):
    warehouse_id = getattr(cfg, "warehouse_id","WH_001") 
    horizon_days = getattr(cfg, "horizon_days", 60)

    log.info(f"🔁 Старт обновления прогнозов по складу {warehouse_id}")

    async with async_session() as session:
        svc = PredictService(
            PredictRepository(session),
            ProductRepository(session), WarehouseRepository(session), SqlAlchemyTransaction(session), Predictor
        )
        try:
            result = await svc.rebuild_predictions_for_warehouse(
                warehouse_id=warehouse_id,
                horizon_days=horizon_days,
            )
            log.info(f"✅ Прогнозы обновлены: {result}")
        except Exception as e:
            log.exception(f"❌ Ошибка при пересчёте прогнозов: {e}")

    log.info(f"🏁 Завершено обновление прогнозов по складу {warehouse_id}")
