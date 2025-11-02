from typing import List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy import select, func,update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.predict import PredictAt
from app.models.product import Product


class PredictRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_last_prediction_time(self, warehouse_id: str):
        result = await self.session.scalar(
            select(func.max(PredictAt.predicted_at))
            .where(PredictAt.warehouse_id == warehouse_id)
        )

        return result 

    async def get_top5_soon_depleted(self, warehouse_id: str):
        stmt = (
        select(
            PredictAt.product_id,
            Product.name.label("product_name"),
            PredictAt.warehouse_id,
            PredictAt.depletion_at.label("p50"),
            PredictAt.depletion_at_p10.label("p10"),
            PredictAt.depletion_at_p90.label("p90"),
            PredictAt.p_deplete_within,
        )
        .join(Product, Product.id == PredictAt.product_id)  
        .where(
            PredictAt.warehouse_id == warehouse_id,
            PredictAt.depletion_at.is_not(None),
        )
        .order_by(PredictAt.depletion_at.asc())
        .limit(5)
        )

        result = await self.session.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def purge_old_predictions(self, days: int = 1) -> int:
        result = (
        delete(PredictAt)
        .where(PredictAt.predicted_at < func.now() - text(f"interval '{days} day'"))
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount or 0

    async def save_predictions(self, results: List[Tuple]):
       if not results:
        return

        rows_to_insert = []
        pairs = set()

        for row in results:
            if len(row) == 4:
                pid, wid, pname, p50 = row
                p10 = p90 = pwithin = None
            elif len(row) == 7:
                pid, wid, pname, p50, p10, p90, pwithin = row
            else:
                continue

            pairs.add((pid, wid))
            rows_to_insert.append({
                "product_id": pid,
                "warehouse_id": wid,
                "product_name": pname,
                "depletion_at": p50,
                "depletion_at_p10": p10,
                "depletion_at_p90": p90,
                "p_deplete_within": pwithin,
                "predicted_at": func.now(),
            })

        if not rows_to_insert:
            return

        pairs_list = list(pairs)
        del_stmt = delete(PredictAt).where(
            tuple_(PredictAt.product_id, PredictAt.warehouse_id).in_(pairs_list)
        )
        await self.session.execute(del_stmt)

        ins_stmt = insert(PredictAt)
        await self.session.execute(ins_stmt, rows_to_insert)

        await self.session.commit()
