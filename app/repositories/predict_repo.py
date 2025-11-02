# app/repositories/predict_repo.py
from typing import List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PredictRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_last_prediction_time(self, warehouse_id: str):
        """Возвращает время последнего прогноза для склада."""
        result = await self.session.execute(
            text("""
            SELECT MAX(predicted_at) AS last_time
            FROM predict_at
            WHERE warehouse_id = :wid
            """),
            {"wid": warehouse_id},
        )
        row = result.mappings().first()
        return row["last_time"] if row and row["last_time"] else None

    async def get_top5_soon_depleted(self, warehouse_id: str):
        """Возвращает 5 ближайших по истощению товаров (с именем и доверительными полями)."""
        result = await self.session.execute(
            text("""
            SELECT
                product_id,
                product_name,
                warehouse_id,
                depletion_at        AS p50,
                depletion_at_p10    AS p10,
                depletion_at_p90    AS p90,
                p_deplete_within
            FROM predict_at
            WHERE warehouse_id = :wid
              AND depletion_at IS NOT NULL
            ORDER BY depletion_at ASC
            LIMIT 5
            """),
            {"wid": warehouse_id},
        )
        return [dict(r) for r in result.mappings().all()]

    async def purge_old_predictions(self, days: int = 1) -> int:
        """Удаляет записи старше N дней. Возвращает число удалённых строк."""
        result = await self.session.execute(
            text("""
            DELETE FROM predict_at
            WHERE predicted_at < NOW() - (:days || ' day')::interval
            """),
            {"days": days},
        )
        await self.session.commit()
        return getattr(result, "rowcount", 0) or 0

    async def save_predictions(self, results: List[Tuple]):
        """
        Сохраняет результаты прогнозов без UPSERT (без UNIQUE-ограничений).

        Поддерживаемые форматы:
          - (product_id, warehouse_id, product_name, p50)
          - (product_id, warehouse_id, product_name, p50, p10, p90, p_within)

        Алгоритм:
          1) DELETE всех старых записей для пары (product_id, warehouse_id)
          2) INSERT новой записи (с p10/p90/p_within, если есть)
        """
        if not results:
            return

        delete_sql = text("""
            DELETE FROM predict_at
            WHERE product_id = :pid AND warehouse_id = :wid
        """)

        insert_sql = text("""
            INSERT INTO predict_at
                (product_id, warehouse_id, product_name,
                 depletion_at, depletion_at_p10, depletion_at_p90,
                 p_deplete_within, predicted_at)
            VALUES
                (:pid, :wid, :pname,
                 :p50, :p10, :p90,
                 :pwithin, NOW())
        """)

        for row in results:
            if len(row) == 4:
                pid, wid, pname, p50 = row
                p10 = p90 = pwithin = None
            elif len(row) == 7:
                pid, wid, pname, p50, p10, p90, pwithin = row
            else:
                # неизвестный формат — пропускаем
                continue

            # 1) зачистить старые
            await self.session.execute(delete_sql, {"pid": pid, "wid": wid})

            # 2) вставить новую
            await self.session.execute(insert_sql, {
                "pid": pid,
                "wid": wid,
                "pname": pname,
                "p50": p50,
                "p10": p10,
                "p90": p90,
                "pwithin": pwithin,
            })

        await self.session.commit()
