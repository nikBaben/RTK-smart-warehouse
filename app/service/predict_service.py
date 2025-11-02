# app/service/predict_service.py
import logging
from datetime import datetime
from typing import List, Dict, Optional

from app.ml.predictor import Predictor
from app.repositories.predict_repo import PredictRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.ml.data_access import fetch_all_product_ids

log = logging.getLogger("service.predict")


class PredictService:
    def __init__(
        self,
        predict_repo: PredictRepository,
        product_repo: Optional[ProductRepository] = None,
        warehouse_repo: Optional[WarehouseRepository] = None,
    ):
        """
        predict_repo  — обязателен (работа с таблицей predict_at)
        product_repo  — опционально (для получения product_name). Если не передан, в product_name пишем product_id.
        warehouse_repo — опционально (нужен для пересчёта по всем складам).
        """
        self.repo = predict_repo
        self.product_repo = product_repo
        self.warehouse_repo = warehouse_repo

    # === Для API: топ-5 ближайших к исчерпанию ===
    async def get_top5_depletion(self, warehouse_id: str) -> List[Dict]:
        """
        Возвращает список из максимум 5 записей:
        [{product_id, product_name, warehouse_id, p50, p10, p90, p_deplete_within}, ...]
        """
        rows = await self.repo.get_top5_soon_depleted(warehouse_id)
        return rows

    # === Пересчёт прогнозов для всех складов ===
    async def rebuild_predictions_for_all_warehouses(self, horizon_days: int = 60):
        if not self.warehouse_repo:
            raise RuntimeError("WarehouseRepository не инициализирован в PredictService")

        warehouse_ids = await self.warehouse_repo.list_ids()
        for wid in warehouse_ids:
            await self.rebuild_predictions_for_warehouse(wid, horizon_days)

    # === Пересчёт прогнозов для одного склада ===
    async def rebuild_predictions_for_warehouse(self, warehouse_id: str, horizon_days: int = 60):
        """
        Формирует и сохраняет прогнозы истощения по всем товарам склада.
        Сохраняет product_name (если доступен через product_repo).
        """
        log.info(f"🔮 Пересчёт прогнозов для склада {warehouse_id}...")
        session = self.repo.session

        # 1) список товаров для склада
        product_ids = await fetch_all_product_ids(session, warehouse_id)
        if not product_ids:
            log.warning(f"⚠️ Нет товаров на складе {warehouse_id}")
            return

        # 2) основной цикл по товарам
        results = []
        for pid in product_ids:
            # имя товара (если есть репозиторий товаров)
            product_name = pid
            try:
                if self.product_repo and hasattr(self.product_repo, "get_name"):
                    # ожидается метод вида: async def get_name(self, product_id: str) -> Optional[str]
                    name = await self.product_repo.get_name(pid)
                    if name:
                        product_name = name
            except Exception as e:
                log.warning(f"Не удалось получить имя товара для {pid}: {e}")

            # путь к персональной модели
            model_path = f"/app/models_store/{pid}.pkl"
            predictor = Predictor(model_path=model_path)  # внутри есть fallback

            try:
                # расширенный прогноз с доверительными интервалами
                if hasattr(predictor, "predict_depletion_with_confidence"):
                    p50, p10, p90, p_within = await predictor.predict_depletion_with_confidence(
                        product_id=pid,
                        warehouse_id=warehouse_id,
                        horizon_days=horizon_days,
                        as_of=datetime.utcnow(),
                    )
                else:
                    # на случай, если метод ещё не влит — используем детерминированный вариант
                    p50 = await predictor.predict_depletion_date(
                        product_id=pid,
                        warehouse_id=warehouse_id,
                        horizon_days=horizon_days,
                        as_of=datetime.utcnow(),
                    )
                    p10 = p90 = None
                    p_within = None

                if p50:
                    # сохраняем с product_name (совместимо с обновлённым PredictRepository.save_predictions)
                    results.append((pid, warehouse_id, product_name, p50, p10, p90, p_within))
                    log.info(f"✅ {pid} ({product_name}): истощение {p50}")
                else:
                    log.info(f"⚠️ {pid} ({product_name}): не удалось рассчитать дату истощения")

            except Exception as e:
                log.error(f"❌ Ошибка при прогнозе {pid}: {e}")

        # 3) сохранение в predict_at
        await self.repo.save_predictions(results)
        log.info(f"💾 Обновлено {len(results)} записей для склада {warehouse_id}")

    async def rebuild_prediction_for_product(
        self,
        warehouse_id: str,
        product_id: str,
        horizon_days: int = 60,
    ) -> Dict:
        product_name = product_id
        try:
            if self.product_repo and hasattr(self.product_repo, "get_name"):
                name = await self.product_repo.get_name(product_id)
                if name:
                    product_name = name
        except Exception as e:
            log.warning(f"Не удалось получить имя товара для {product_id}: {e}")

        predictor = Predictor(model_path=f"/app/models_store/{product_id}.pkl")

        p50, p10, p90, p_within = await predictor.predict_depletion_with_confidence(
            product_id=product_id,
            warehouse_id=warehouse_id,
            horizon_days=horizon_days,
            as_of=datetime.utcnow(),
        )

        if p50:
            await self.repo.save_predictions([
                (product_id, warehouse_id, product_name, p50, p10, p90, p_within)
            ])

        return {
            "product_id": product_id,
            "product_name": product_name,
            "warehouse_id": warehouse_id,
            "horizon_days": horizon_days,
            "depletion_at": p50.isoformat() if p50 else None,
            "p10": p10.isoformat() if p10 else None,
            "p90": p90.isoformat() if p90 else None,
            "p_deplete_within": p_within,
            "persisted": bool(p50),
        }