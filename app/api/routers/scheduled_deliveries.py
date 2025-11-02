from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import async_session
from app.models.delivery import ScheduledDelivery
from app.models.product import Product
from app.models.warehouse import Warehouse

router = APIRouter(prefix="/scheduled_deliveries", tags=["deliveries"])

#Pydantic схемы
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
    def ensure_future(cls, v: datetime):
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

class ScheduledDeliveryOut(BaseModel):
    id: str
    product_id: str
    warehouse_id: str
    scheduled_at: datetime
    quantity: int
    status: str = "scheduled"
    supplier: Optional[str] = None
    notes: Optional[str] = None

@router.post("", response_model=ScheduledDeliveryOut, status_code=201)
async def create_scheduled_delivery(payload: ScheduledDeliveryIn):
    async with async_session() as session:
        prod_exists = await session.scalar(
            select(Product.id).where(Product.id == payload.product_id)
        )
        if not prod_exists:
            raise HTTPException(status_code=404, detail="Product not found")

        wh_exists = await session.scalar(
            select(Warehouse.id).where(Warehouse.id == payload.warehouse_id)
        )
        if not wh_exists:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        existing = await session.get(ScheduledDelivery, payload.id)
        if existing:
            return ScheduledDeliveryOut(
                id=existing.id,
                product_id=existing.product_id,
                warehouse_id=existing.warehouse_id,
                scheduled_at=existing.scheduled_at,
                quantity=existing.quantity,
                status=existing.status,
                supplier=existing.supplier,
                notes=existing.notes,
            )

        obj = ScheduledDelivery(
            id=payload.id,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            scheduled_at=payload.scheduled_at if payload.scheduled_at.tzinfo else payload.scheduled_at.replace(tzinfo=timezone.utc),
            quantity=payload.quantity,
            status="scheduled",
            supplier=payload.supplier,
            notes=payload.notes,
        )
        session.add(obj)

        try:
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            existing = await session.get(ScheduledDelivery, payload.id)
            if existing:
                return ScheduledDeliveryOut(
                    id=existing.id,
                    product_id=existing.product_id,
                    warehouse_id=existing.warehouse_id,
                    scheduled_at=existing.scheduled_at,
                    quantity=existing.quantity,
                    status=existing.status,
                    supplier=existing.supplier,
                    notes=existing.notes,
                )
            raise HTTPException(status_code=400, detail=f"Integrity error: {str(e.orig) if hasattr(e, 'orig') else str(e)}")

        return ScheduledDeliveryOut(
            id=obj.id,
            product_id=obj.product_id,
            warehouse_id=obj.warehouse_id,
            scheduled_at=obj.scheduled_at,
            quantity=obj.quantity,
            status=obj.status,
            supplier=obj.supplier,
            notes=obj.notes,
        )
