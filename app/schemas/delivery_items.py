from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, conint

QuantityType = conint(ge=0)


class DeliveryItemsBase(BaseModel):
    ordered_quantity: QuantityType = Field(..., description="Запланированное количество товара")
    fact_quantity: QuantityType = Field(..., description="Фактическое количество полученного контекта")


class DeliveryItemsCreate(DeliveryItemsBase):
    id: Optional[str] = Field(None, description="Optional id")
    delivery_id: Optional[str] = Field(None, description="delivery id")
    product_id: Optional[str] = Field(None, description="product_id")
    warehouse_id: Optional[str] = Field(None, description="warehouse_id")


class DeliveryItemsRead(BaseModel):
    id: str
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True