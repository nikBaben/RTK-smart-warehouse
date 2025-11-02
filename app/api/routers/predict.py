from fastapi import APIRouter, Query, HTTPException,Depends
from typing import Optional
from datetime import datetime
from app.ml.predictor import Predictor
import os
from app.service.predict_service import PredictService
from app.api.deps import get_predict_service
from app.schemas.predict import PredictResponse

router = APIRouter(prefix="/ml", tags=["ml"])

@router.post("/depletion", summary="Посчитать и сохранить прогноз истощения для одного товара")
async def rebuild_and_upsert_depletion(
    product_id: str = Query(...),
    warehouse_id: str = Query(...),
    horizon_days: int = 60,
    svc: PredictService = Depends(get_predict_service),
):
    """
    Считает прогноз для (product_id, warehouse_id) и сохраняет/обновляет запись в predict_at.
    Возвращает рассчитанные значения.
    """
    try:
        result = await svc.rebuild_prediction_for_product(
            warehouse_id=warehouse_id,
            product_id=product_id,
            horizon_days=horizon_days,
        )
        # Если p50 не посчитан — вернём 204/404 на твой вкус. Я оставлю 200 с None.
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расчёта/сохранения прогноза: {e}")


@router.get(
    "/soon_depleted",
    response_model=list[PredictResponse],
    summary="Топ-5 ближайших к исчерпанию товаров по складу",
    )
async def get_top5_soon_depleted(
    warehouse_id: str = Query(..., description="ID склада"),
    service: PredictService = Depends(get_predict_service),
):
    """
    Возвращает 5 ближайших товаров по дате истощения.
    """
    data = await service.get_top5_depletion(warehouse_id)
    return data