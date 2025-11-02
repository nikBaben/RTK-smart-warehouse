from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, conint

from app.models.enums import DeliveryStatus

QuantityType = conint(ge=0)


class DeliveryBase(BaseModel):
    name: Optional[str] = Field(None, description="Название поставки")
    scheduled_at: datetime = Field(..., description="Запланированное время доставки")
    delivered_at: datetime = Field(None, description="Фактическое время доставки")
    quantity: QuantityType = Field(..., description="Запланированное количество доставляемого товара")
    status: DeliveryStatus = Field(DeliveryStatus.scheduled, description="Статус доставки. Может быть:\n" +
                                  "scheduled - запланированно\n" +
                                  "arrived - заказ доставлен\n" +
                                  "canceled - доставка отменена\n" +
                                  "rescheduled - время доставки изменено")
    supplier: Optional[str] = Field(None, description="Имя поставщика")
    notes: Optional[str] = Field(None, description="Дополнительные заметки")
    
    
class DeliveryCreate(DeliveryBase):
    id: Optional[str] = Field(None, description="Optional id")
    warehouse_id: Optional[str] = Field(None, description="warehouse id")


class DeliveryRead(DeliveryBase):
    id: str
    status: DeliveryStatus
    created_at: datetime
    
    class Config:
        from_attributes = True