from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.ml.predictor import Predictor
from app.repositories.predict_repo import PredictRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.schemas.predict import PredictResponse
from app.ml.data_access import fetch_all_product_ids

log = logging.getLogger("service.predict")


class PredictService:
    def __init__(
        self,
        predict_repo: PredictRepository,
        product_repo: Optional[ProductRepository] = None,
        warehouse_repo: Optional[WarehouseRepository] = None,
        default_model_path: Optional[str] = "/app/models_store/PROD_DEMO.pkl",
    ):
        self.repo = predict_repo
        self.product_repo = product_repo
        self.warehouse_repo = warehouse_repo
        self.default_model_path = default_model_path

    async def get_top5_depletion(self, warehouse_id: str) -> List[PredictResponse]:
        rows = await self.repo.get_top5_soon_depleted(warehouse_id)
        items = []
        for row in rows:
            pid = row["product_id"]
            stock = await self.product_repo.get_stock(pid) if self.product_repo else None
            required = await self.product_repo.required_delivery(pid) if self.product_repo else None
            items.append(PredictResponse(
                product_id=row["product_id"],
                product_name=row["product_name"],
                warehouse_id=row["warehouse_id"],
                depletion_date=row["p50"],
                reliability=row["p_deplete_within"],
                stock=stock,
                required_delivery=required,
            ))
        return items

    async def rebuild_predictions_for_all_warehouses(self, horizon_days: int = 60):
        if not self.warehouse_repo:
            raise RuntimeError("WarehouseRepository не инициализирован в PredictService")
        warehouse_ids = await self.warehouse_repo.list_ids()
        for wid in warehouse_ids:
            await self.rebuild_predictions_for_warehouse(wid, horizon_days)

    async def rebuild_predictions_for_warehouse(self, warehouse_id: str, horizon_days: int = 60):
        log.info(f"🔮 Пересчёт прогнозов для склада {warehouse_id}...")
        session = self.repo.session
        product_ids = await fetch_all_product_ids(session, warehouse_id)
        if not product_ids:
            log.warning(f"⚠️ Нет товаров на складе {warehouse_id}")
            return

        results = []
        for pid in product_ids:
            product_name = pid
            try:
                if self.product_repo and hasattr(self.product_repo, "get_nam"):
                    name = await self.product_repo.get_nam(pid)
                    if name:
                        product_name = name
            except Exception as e:
                log.warning(f"Не удалось получить имя товара для {pid}: {e}")

            predictor = Predictor(
                model_path=f"/app/models_store/{pid}.pkl",
                default_model_path=self.default_model_path,
            )
            try:
                p50, p10, p90, p_within = await predictor.predict_depletion_with_confidence(
                    product_id=pid,
                    warehouse_id=warehouse_id,
                    horizon_days=horizon_days,
                    as_of=datetime.now(timezone.utc),
                    within_days=horizon_days,  # вероятность истощения в пределах горизонта
                )
                if p50:
                    results.append((pid, warehouse_id, product_name, p50, p10, p90, p_within))
                    log.info(f"✅ {pid} ({product_name}): истощение {p50}")
                else:
                    log.info(f"⚠️ {pid} ({product_name}): не удалось рассчитать дату истощения")
            except Exception as e:
                log.error(f"❌ Ошибка при прогнозе {pid}: {e}")

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
            if self.product_repo and hasattr(self.product_repo, "get_nam"):
                name = await self.product_repo.get_nam(product_id)
                if name:
                    product_name = name
        except Exception as e:
            log.warning(f"Не удалось получить имя товара для {product_id}: {e}")

        predictor = Predictor(
            model_path=f"/app/models_store/{product_id}.pkl",
            default_model_path=self.default_model_path,
        )
        p50, p10, p90, p_within = await predictor.predict_depletion_with_confidence(
            product_id=product_id,
            warehouse_id=warehouse_id,
            horizon_days=horizon_days,
            as_of=datetime.now(timezone.utc),
            within_days=horizon_days,
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
