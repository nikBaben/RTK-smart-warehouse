from __future__ import annotations

from typing import List, Tuple, Optional
from datetime import datetime, timezone

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import tuple_

from app.models.predict import PredictAt
from app.models.product import Product


class PredictRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_last_prediction_time(self, warehouse_id: str) -> Optional[datetime]:
        return await self.session.scalar(
            select(func.max(PredictAt.predicted_at)).where(PredictAt.warehouse_id == warehouse_id)
        )

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
        # удаляем старые предикты (старше N дней)
        del_stmt = delete(PredictAt).where(
            PredictAt.predicted_at < func.now() - func.make_interval(0, 0, 0, days)
        )
        result = await self.session.execute(del_stmt)
        await self.session.commit()
        return result.rowcount or 0

    async def save_predictions(self, results: List[Tuple]) -> None:
        """
        results:
          - 4-элем.: (product_id, warehouse_id, product_name, p50)
          - 7-элем.: (product_id, warehouse_id, product_name, p50, p10, p90, p_within)
        """
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
                # неподдерживаемый формат
                continue

            pairs.add((pid, wid))
            rows_to_insert.append(
                {
                    "product_id": pid,
                    "warehouse_id": wid,
                    "product_name": pname,
                    "depletion_at": p50,
                    "depletion_at_p10": p10,
                    "depletion_at_p90": p90,
                    "p_deplete_within": pwithin,
                    # ВАРИАНТ А (рекомендуется): не указываем predicted_at — пусть сработает server_default=now() в модели
                    # "predicted_at": НЕ УКАЗЫВАЕМ

                    # ВАРИАНТ B: если нет server_default в модели, раскомментируй строку ниже (python-время UTC):
                    # "predicted_at": datetime.now(timezone.utc),
                }
            )

        if not rows_to_insert:
            return

        # 1) удаляем существующие записи для этих пар (product_id, warehouse_id)
        pairs_list = list(pairs)
        del_stmt = delete(PredictAt).where(tuple_(PredictAt.product_id, PredictAt.warehouse_id).in_(pairs_list))
        await self.session.execute(del_stmt)

        # 2) массовая вставка
        ins_stmt = insert(PredictAt)
        await self.session.execute(ins_stmt, rows_to_insert)

        await self.session.commit()
