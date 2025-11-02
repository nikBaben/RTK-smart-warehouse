from uuid import uuid4
from typing import Optional
from app.repositories.delivery_items_repo import DeliveryItemsRepository
from app.schemas.delivery_items import DeliveryItemsCreate


class DeliveryItemsService:
    def __init__(self, repo: DeliveryItemsRepository):
        self.repo = repo
        
    async def create_delivery_items(self, data: DeliveryItemsCreate):
        sd_id = data.id or str(uuid4())
        sd = await self.repo.create(
            id=sd_id,
            delivery_id=data.delivery_id,
            product_id=data.product_id,
            warehouse_id=data.warehouse_id,
            ordered_quantity=data.ordered_quantity,
            fact_quantity=data.fact_quantity
        )
        
        return sd
    
    async def get(self, id: str):
        return await self.repo.get(id)
    
    async def get_by_delivery_id(self, delivery_id: str):
        return await self.repo.get_by_delivery_id(delivery_id)
    
    async def get_by_warehouse_id(self, warehouse_id: str):
        return await self.repo.get_by_warehouse_id(warehouse_id)