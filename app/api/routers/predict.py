import os
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException,Depends
from typing import Optional
from app.ml.predictor import Predictor
from app.service.predict_service import PredictService
from app.api.deps import get_predict_service
from app.schemas.predict import PredictResponse

router = APIRouter(prefix="/ml", tags=["ml"])

@router.post(
    "/depletion",
    summary="Исчерпание для одного товара - Прогноз ИИ ",
)
async def rebuild_and_upsert_depletion(
    product_id: str = Query(..., description="ID товара"),
    warehouse_id: str = Query(..., description="ID склада"),
    horizon_days: int = 30,
    svc: PredictService = Depends(get_predict_service),
):
    try:
        result = await svc.rebuild_prediction_for_product(
            warehouse_id=warehouse_id,
            product_id=product_id,
            horizon_days=horizon_days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расчёта/сохранения прогноза: {e}")

@router.get(
    "/soon_depleted",
    response_model=list[PredictResponse],
    summary="Топ-5 ближайших к исчерпанию товаров по складу - прогноз ИИ",
    response_model_by_alias=False
    )
async def get_top5_soon_depleted(
    warehouse_id: str = Query(..., description="ID склада"),
    service: PredictService = Depends(get_predict_service),
):
    data = await service.get_top5_depletion(warehouse_id)
    return data