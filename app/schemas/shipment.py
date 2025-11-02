from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, conint

from app.models.enums import ShipmentStatus

QuantityType = conint(ge=0)


class ShipmentBase(BaseModel):
    name: Optional[str] = Field(None, description="Название отгрузки")
    scheduled_at: datetime = Field(..., description="Запланированное время доставки до пункта назначения")
    shipped_at: Optional[datetime] = Field(None, description="Фактическое время доставки")
    quantity: QuantityType = Field(..., description="Запланированное количество товара")
    status: ShipmentStatus = Field(ShipmentStatus.scheduled, description="Статус отгрузки")
    customer: Optional[str] = Field(None, description="Имя заказчика")
    notes: Optional[str] = Field(None, description="Дополнительные ")

class ShipmentCreate(ShipmentBase):
    id: Optional[str] = Field(None, description="Optinal id")
    warehouse_id: Optional[str] = Field(None, description="warehouse_id")
    
class ShipmentRead(ShipmentBase):
    id: str
    status: ShipmentStatus
    created_at: datetime
    
    class Config:
        from_attribute = True
        
