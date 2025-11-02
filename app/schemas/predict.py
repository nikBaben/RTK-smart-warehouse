from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PredictResponse(BaseModel):
    product_id: str
    product_name: str
    warehouse_id: str
    depletion_date: datetime = Field(..., alias="depletion_at") 
    reliability: int  = Field(..., alias="p_deplete_within") 
    stock: Optional[int] = Field(None, description="Текущий остаток товара")
    required_delivery: Optional[int] = Field(None, description="Сколько докупить до optimal_stock")

    class Config:
        populate_by_name = True  

