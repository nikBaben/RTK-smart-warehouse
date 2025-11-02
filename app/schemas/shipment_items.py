from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, conint

QuantityType = conint(ge=0)


class ShipmentItemBase(BaseModel):
    ordered_quantity: QuantityType = Field(..., description="Запланированное количество отгрузки")
    fact_quantity: QuantityType = Field(..., description="фактическое количество отгрузки")

class ShipmentItemsCreate(ShipmentItemBase):
    id: Optional[str] = Field(None, description="Optional id")
    shipment_id: Optional[str] = Field(None, description="shipment id")
    product_id: Optional[str] = Field(None, description="product id")
    warehouse_id: Optional[str] = Field(None, description="warehouse id")


class ShipmentItemsRead(BaseModel):
    id: str
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True