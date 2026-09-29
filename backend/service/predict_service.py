import logging
from datetime import datetime, timezone
from backend.ports import (
    PredictRepository,
    ProductRepository,
    WarehouseRepository,
    Transaction,
    PredictorFactory,
)
from backend.schemas.predict import PredictResponse

log = logging.getLogger(__name__)


class PredictService:
    def __init__(
        self,
        predict_repo: PredictRepository,
        product_repo: ProductRepository,
        warehouse_repo: WarehouseRepository,
        transaction: Transaction,
        predictor_factory: PredictorFactory,
    ):
        self.repo = predict_repo
        self.product_repo = product_repo
        self.warehouse_repo = warehouse_repo
        self.transaction = transaction
        self.predictor_factory = predictor_factory

    async def get_top5_depletion(self, warehouse_id: str) -> list[PredictResponse]:
        rows = await self.repo.get_top5_soon_depleted(warehouse_id)
        return [
            PredictResponse(
                product_id=row["product_id"],
                product_name=row["product_name"],
                warehouse_id=row["warehouse_id"],
                depletion_date=row["p50"],
                reliability=row["p_deplete_within"],
                stock=await self.product_repo.get_stock(row["product_id"]),
                required_delivery=await self.product_repo.required_delivery(
                    row["product_id"]
                ),
            )
            for row in rows
        ]

    async def _predict(self, warehouse_id: str, product_id: str, horizon_days: int):
        name = await self.product_repo.get_name(product_id) or product_id
        predictor = self.predictor_factory(
            model_path=f"/backend/models_store/{product_id}.pkl"
        )
        p50, p10, p90, within = await predictor.predict_depletion_with_confidence(
            product_id=product_id,
            warehouse_id=warehouse_id,
            horizon_days=horizon_days,
            as_of=datetime.now(timezone.utc),
        )
        return product_id, warehouse_id, name, p50, p10, p90, within

    async def rebuild_predictions_for_all_warehouses(self, horizon_days: int = 60):
        for warehouse_id in await self.warehouse_repo.list_ids():
            await self.rebuild_predictions_for_warehouse(warehouse_id, horizon_days)

    async def rebuild_predictions_for_warehouse(
        self, warehouse_id: str, horizon_days: int = 60
    ):
        results = []
        for product_id in await self.product_repo.list_ids(warehouse_id):
            try:
                row = await self._predict(warehouse_id, product_id, horizon_days)
                if row[3] is not None:
                    results.append(row)
            except Exception:
                log.exception("Prediction failed for product %s", product_id)
        async with self.transaction:
            await self.repo.save_predictions(results)
            await self.transaction.commit()
        return len(results)

    async def rebuild_prediction_for_product(
        self, warehouse_id: str, product_id: str, horizon_days: int = 60
    ):
        row = await self._predict(warehouse_id, product_id, horizon_days)
        _, _, name, p50, p10, p90, within = row
        if p50 is not None:
            async with self.transaction:
                await self.repo.save_predictions([row])
                await self.transaction.commit()
        return dict(
            product_id=product_id,
            product_name=name,
            warehouse_id=warehouse_id,
            horizon_days=horizon_days,
            depletion_at=p50.isoformat() if p50 else None,
            p10=p10.isoformat() if p10 else None,
            p90=p90.isoformat() if p90 else None,
            p_deplete_within=within,
            persisted=p50 is not None,
        )
