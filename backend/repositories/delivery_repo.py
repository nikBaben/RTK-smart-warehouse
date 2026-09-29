from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.models.delivery import Delivery
from backend.domain.enums import DeliveryStatus


class DeliveryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        id: str,
        warehouse_id: Optional[str],
        scheduled_at,
        quantity: int,
        delivered_at,
        name: Optional[str] = None,
        status: Optional[DeliveryStatus] = DeliveryStatus.scheduled,
        supplier: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Delivery:
        sd = Delivery(
            id=id,
            name=name,
            warehouse_id=warehouse_id,
            scheduled_at=scheduled_at,
            delivered_at=delivered_at,
            quantity=quantity,
            status=status,
            supplier=supplier,
            notes=notes,
        )
        self.session.add(sd)
        await self.session.flush()
        await self.session.refresh(sd)
        return sd

    async def get(self, id: str) -> Optional[Delivery]:
        return await self.session.scalar(select(Delivery).where(Delivery.id == id))

    async def mark_arrived(self, id: str) -> Optional[Delivery]:
        stmt = (
            update(Delivery)
            .where(Delivery.id == id)
            .values(status=DeliveryStatus.arrived)
            .returning(Delivery)
        )
        result = await self.session.execute(stmt)
        return result.scalars().one_or_none()

    async def delete(self, id: str) -> bool:
        stmt = delete(Delivery).where(Delivery.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
