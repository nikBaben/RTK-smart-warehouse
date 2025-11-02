from uuid import uuid4
from typing import List, Optional
from app.repositories.delivery_repo import DeliveryRepository
from app.schemas.delivery import DeliveryCreate
from app.models.enums import DeliveryStatus
from app.repositories.delivery_items_repo import DeliveryItemsRepository
from app.schemas.supplies import DeliveryDetailResponse, DeliveryItemDetailResponse


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
    
    async def get_delivery_by_id(self, delivery_id: str) -> Optional[DeliveryDetailResponse]:
        """Получить доставку по ID"""
        delivery = await self.repo.get(delivery_id)
        if not delivery:
            return None
        
        return DeliveryDetailResponse(
            id=delivery.id,
            name=delivery.name,
            warehouse_id=delivery.warehouse_id,
            scheduled_at=delivery.scheduled_at,
            delivered_at=delivery.delivered_at,
            quantity=delivery.quantity,
            status=delivery.status,
            supplier=delivery.supplier,
            notes=delivery.notes,
            created_at=delivery.created_at
        )

    async def get_delivery_items(self, delivery_id: str) -> List[DeliveryItemDetailResponse]:
        """Получить элементы доставки"""
        items = await self.items_repo.get_by_delivery_id(delivery_id)
        
        return [
            DeliveryItemDetailResponse(
                id=item.id,
                delivery_id=item.delivery_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                ordered_quantity=item.ordered_quantity,
                fact_quantity=item.fact_quantity,
                created_at=item.created_at
            )
            for item in items
        ]

    async def get_delivery_item_by_id(self, item_id: str) -> Optional[DeliveryItemDetailResponse]:
        """Получить элемент доставки по ID"""
        item = await self.items_repo.get(item_id)
        if not item:
            return None
        
        return DeliveryItemDetailResponse(
            id=item.id,
            delivery_id=item.delivery_id,
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            ordered_quantity=item.ordered_quantity,
            fact_quantity=item.fact_quantity,
            created_at=item.created_at
        )
    
    async def delete_delivery(self, delivery_id: str) -> bool:
        try:
            await self.items_repo.delete_by_delivery_id(delivery_id)
            return await self.repo.delete(delivery_id)
        except Exception:
            return False

    async def delete_delivery_item(self, item_id: str) -> bool:
        return await self.items_repo.delete(item_id)
    
    async def mark_arrived(self, id: str):
        return await self.repo.mark_arrived(id)