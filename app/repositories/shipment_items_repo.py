from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.shipment import ShipmentItems


class ShipmentItemsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, id: str, shipment_id: Optional[str],
                     product_id: Optional[str], warehouse_id: Optional[str], ordered_quantity: int,
                     fact_quantity: int) -> ShipmentItems:
        si = ShipmentItems(
            id=id,
            shipment_id=shipment_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            ordered_quantity=ordered_quantity,
            fact_quantity=fact_quantity,
        )
        async with self.session.begin():
            self.session.add(si)
            await self.session.refresh(si)
        return si

    async def get(self, id: str) -> Optional[ShipmentItems]:
        return await self.session.scalar(
            select(ShipmentItems).where(ShipmentItems.id == id)
        )

    async def get_by_shipment_id(self, shipment_id: str) -> List[ShipmentItems]:
        result = await self.session.execute(
            select(ShipmentItems).where(ShipmentItems.shipment_id == shipment_id)
        )
        return result.scalars().all()

    async def get_by_warehouse_id(self, warehouse_id: str) -> List[ShipmentItems]:
        result = await self.session.execute(
            select(ShipmentItems).where(ShipmentItems.warehouse_id == warehouse_id)
        )
        return result.scalars().all()
    
    async def delete(self, id: str) -> bool:
        stmt = delete(ShipmentItems).where(ShipmentItems.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_by_shipment_id(self, shipment_id: str) -> bool:
        stmt = delete(ShipmentItems).where(ShipmentItems.shipment_id == shipment_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0