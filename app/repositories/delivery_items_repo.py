from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.delivery_items import DeliveryItems


class DeliveryItemsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, *, id: str, delivery_id: Optional[str],
                     product_id: Optional[str], warehouse_id: Optional[str],
                     ordered_quantity: int, fact_quantity: int) -> DeliveryItems:
        sd = DeliveryItems(
            id=id,
            delivery_id=delivery_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            ordered_quantity=ordered_quantity,
            fact_quantity=fact_quantity
        )
        async with self.session.begin():
            self.session.add(sd)
            await self.session.refresh(sd)
        return sd
    
    async def get(self, id: str) -> Optional[DeliveryItems]:
        return await self.session.scalar(
            select(DeliveryItems)\
            .where(DeliveryItems.id == id)
        )
    
    async def get_by_delivery_id(self, delivery_id: str) -> List[DeliveryItems]:
        result = await self.session.execute(
            select(DeliveryItems)\
            .where(DeliveryItems.delivery_id == delivery_id)
        )
        return result.scalars().all()
    
    async def get_by_warehouse_id(self, warehouse_id: str) -> List[DeliveryItems]:
        result = await self.session.execute(
            select(DeliveryItems)\
            .where(DeliveryItems.warehouse_id == warehouse_id)
        )
        return result.scalars().all()
    
    async def delete(self, id: str) -> bool:
        stmt = delete(DeliveryItems).where(DeliveryItems.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_by_delivery_id(self, delivery_id: str) -> bool:
        stmt = delete(DeliveryItems).where(DeliveryItems.delivery_id == delivery_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0