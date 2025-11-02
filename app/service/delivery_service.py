from uuid import uuid4
from typing import Optional
from app.repositories.delivery_repo import DeliveryRepository
from app.schemas.delivery import DeliveryCreate
from app.models.enums import DeliveryStatus
from app.repositories.delivery_items_repo import DeliveryItemsRepository


class DeliveryService:
    def __init__(self, repo: DeliveryRepository,
                 items_repo: DeliveryItemsRepository):
        self.repo = repo
        self.items_repo = items_repo
    
    async def create_delivery(self, data: DeliveryCreate):
        sd_id = data.id or str(uuid4())
        sd = await self.repo.create(
            id=sd_id,
            warehouse_id=data.warehouse_id,
            scheduled_at=data.scheduled_at,
            delivered_at=data.delivered_at,
            quantity=int(data.quantity),
            status=data.status if isinstance(data.status, DeliveryStatus) else DeliveryStatus(data.status),
            supplier=data.supplier,
            notes=data.notes
        )
        
        return sd
    
    async def add_item(self, data):
        sd_id = getattr(data, "id", None) or str(uuid4())
        sd = await self.items_repo.create(
            id=sd_id,
            delivery_id=getattr(data, "delivery_id"),
            product_id=getattr(data, "product_id"),
            warehouse_id=getattr(data, "product_id"),
            ordered_quantity=getattr(data, "ordered_quantity", 0),
            fact_quantity=getattr(data, "fact_quantity", 0)
        )
        return sd
    
    async def get(self, id: str):
        return await self.repo.get(id)
    
    async def mark_arrived(self, id: str):
        return await self.repo.mark_arrived(id)