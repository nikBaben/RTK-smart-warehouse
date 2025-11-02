from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.shipment import Shipment


class ShipmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, id: str, warehouse_id: Optional[str], name: Optional[str],
                     scheduled_at, shipped_at: Optional[object], quantity: int, status: Optional[object],
                     customer: Optional[str], notes: Optional[str]) -> Shipment:
        sh = Shipment(
            id=id,
            warehouse_id=warehouse_id,
            name=name,
            scheduled_at=scheduled_at,
            shipped_at=shipped_at,
            quantity=quantity,
            status=status,
            customer=customer,
            notes=notes,
        )
        async with self.session.begin():
            self.session.add(sh)
            await self.session.refresh(sh)
        return sh

    async def get(self, id: str) -> Optional[Shipment]:
        return await self.session.scalar(
            select(Shipment).where(Shipment.id == id)
        )

    async def list_for_warehouse(self, warehouse_id: str):
        result = await self.session.execute(
            select(Shipment).where(Shipment.warehouse_id == warehouse_id)
        )
        return result.scalars().all()
    
    async def delete(self, id: str) -> bool:
        stmt = delete(Shipment).where(Shipment.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0