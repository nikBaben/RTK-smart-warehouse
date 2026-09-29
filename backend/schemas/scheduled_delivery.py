from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ScheduledDeliveryIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, description="Уникальный ID плана")
    product_id: str = Field(..., min_length=1, max_length=50)
    warehouse_id: str = Field(..., min_length=1, max_length=50)
    scheduled_at: datetime = Field(..., description="ISO8601, UTC предпочтительно")
    quantity: int = Field(..., gt=0, description="Плановое количество (> 0)")
    supplier: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("scheduled_at")
    @classmethod
    def normalize_timezone(cls, v: datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v


class ScheduledDeliveryOut(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    product_id: str
    warehouse_id: str
    scheduled_at: datetime
    quantity: int
    status: str = "scheduled"
    supplier: Optional[str] = None
    notes: Optional[str] = None
