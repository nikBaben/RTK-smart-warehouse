# app/ml/predict_all.py
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ⚠️ Важно: у тебя сессия называется async_session в app.db.session
# Если у тебя алиас другой — поправь строку импорта ниже.
from app.db.session import async_session as async_session_maker

from app.ml.predictor import Predictor
from app.ml.data_access import fetch_all_product_ids


async def predict_all_for_warehouse(
    warehouse_id: str,
    horizon_days: int = 60,
    default_model_path: str = "/app/models_store/PROD_DEMO.pkl",
) -> None:
    """
    Прогоняет прогноз истощения для всех товаров склада и складывает результаты в predict_at.
    """
    async with async_session_maker() as session:
        # 1) список товаров
        product_ids = await fetch_all_product_ids(session, warehouse_id)
        print(f"Всего товаров для прогноза (склад {warehouse_id}): {len(product_ids)}")

        results: List[Tuple[str, str, datetime]] = []

        for pid in product_ids:
            model_path = f"/app/models_store/{pid}.pkl"
            predictor = Predictor(model_path=model_path, default_model_path=default_model_path)

            try:
                depletion = await predictor.predict_depletion_date(
                    product_id=pid,
                    warehouse_id=warehouse_id,
                    horizon_days=horizon_days,
                    as_of=datetime.utcnow(),  # naive → так же используем везде
                )
                if depletion:
                    results.append((pid, warehouse_id, depletion))
                    print(f"✅ {pid}: истощение {depletion}")
                else:
                    print(f"⚠️ {pid}: не удалось рассчитать")
            except Exception as e:
                print(f"❌ Ошибка для {pid}: {e}")

        await save_predictions(session, results)


async def save_predictions(session: AsyncSession, results: List[Tuple[str, str, datetime]]) -> None:
    """
    Сохраняем результаты в predict_at.
    Политика очистки: удаляем записи старше 1 дня.
    """
    if not results:
        print("Нет данных для сохранения")
        return

    await session.execute(
        text("DELETE FROM predict_at WHERE predicted_at < NOW() - INTERVAL '1 day'")
    )

    for pid, wid, dt in results:
        await session.execute(
            text(
                """
                INSERT INTO predict_at (product_id, warehouse_id, depletion_at, predicted_at)
                VALUES (:pid, :wid, :dt, NOW())
                """
            ),
            {"pid": pid, "wid": wid, "dt": dt},
        )

    await session.commit()
    print(f"💾 Сохранено {len(results)} записей в predict_at")


def main():
    parser = argparse.ArgumentParser(description="Batch-предсказания истощения по складу")
    parser.add_argument("--warehouse-id", required=True, help="ID склада")
    parser.add_argument("--horizon-days", type=int, default=60, help="Горизонт прогноза в днях")
    parser.add_argument(
        "--default-model-path",
        default="/app/models_store/PROD_DEMO.pkl",
        help="Путь к базовой (fallback) модели, если персональной нет",
    )
    args = parser.parse_args()

    asyncio.run(
        predict_all_for_warehouse(
            warehouse_id=args.warehouse_id,
            horizon_days=args.horizon_days,
            default_model_path=args.default_model_path,
        )
    )


if __name__ == "__main__":
    main()
