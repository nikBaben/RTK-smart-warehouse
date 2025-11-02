from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PredictResponse(BaseModel):
    product_id: str = Field(..., description="ID товара")
    product_name: str = Field(..., description="Название товара")
    depletion_at: Optional[datetime] = Field(None, alias="p50", description="Ожидаемая дата истощения")
    depletion_at_p10: Optional[datetime] = Field(None, alias="p10", description="Быстрая (ранняя) дата истощения")
    depletion_at_p90: Optional[datetime] = Field(None, alias="p90", description="Поздняя (медленная) дата истощения")
    p_deplete_within: Optional[float] = Field(None, description="Достоверность прогноза (0.0–1.0)")
    warehouse_id: str = Field(..., description="ID склада")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,   # позволяет использовать alias при возврате
    )
