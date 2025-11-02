from uuid import uuid4
from typing import List, Optional
from app.repositories.shipment_repo import ShipmentRepository
from app.repositories.shipment_items_repo import ShipmentItemsRepository
from app.schemas.shipment_items import ShipmentItemsCreate
from app.schemas.shipment import ShipmentCreate
from app.schemas.supplies import ShipmentDetailResponse, ShipmentItemDetailResponse


class ShipmentService:
    def __init__(self, repo: ShipmentRepository, items_repo: ShipmentItemsRepository):
        self.repo = repo
        self.items_repo = items_repo

    async def create_shipment(self, data: ShipmentCreate):
        sh_id = getattr(data, "id", None) or str(uuid4())
        sh = await self.repo.create(
            id=sh_id,
            warehouse_id=getattr(data, "warehouse_id", None),
            name=getattr(data, "name", None),
            scheduled_at=getattr(data, "scheduled_at"),
            shipped_at=getattr(data, "shipped_at", None),
            quantity=getattr(data, "quantity", 0),
            status=getattr(data, "status", None),
            customer=getattr(data, "customer", None),
            notes=getattr(data, "notes", None),
        )
        return sh

    async def add_item(self, data: ShipmentItemsCreate):
        si_id = getattr(data, "id", None) or str(uuid4())
        si = await self.items_repo.create(
            id=si_id,
            shipment_id=getattr(data, "shipment_id"),
            product_id=getattr(data, "product_id"),
            warehouse_id=getattr(data, "warehouse_id", None),
            ordered_quantity=getattr(data, "ordered_quantity", 0),
            fact_quantity=getattr(data, "fact_quantity", 0),
        )
        return si
    
    async def get_shipment_by_id(self, shipment_id: str) -> Optional[ShipmentDetailResponse]:
        """Получить отгрузку по ID"""
        shipment = await self.repo.get(shipment_id)
        if not shipment:
            return None
        
        return ShipmentDetailResponse(
            id=shipment.id,
            name=shipment.name,
            warehouse_id=shipment.warehouse_id,
            scheduled_at=shipment.scheduled_at,
            shipped_at=shipment.shipped_at,
            quantity=shipment.quantity,
            status=shipment.status,
            customer=shipment.customer,
            notes=shipment.notes,
            created_at=shipment.created_at
        )

    async def get_shipment_items(self, shipment_id: str) -> List[ShipmentItemDetailResponse]:
        """Получить элементы отгрузки"""
        items = await self.items_repo.get_by_shipment_id(shipment_id)
        
        return [
            ShipmentItemDetailResponse(
                id=item.id,
                shipment_id=item.shipment_id,
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                ordered_quantity=item.ordered_quantity,
                fact_quantity=item.fact_quantity,
                created_at=item.created_at
            )
            for item in items
        ]

    async def get_shipment_item_by_id(self, item_id: str) -> Optional[ShipmentItemDetailResponse]:
        """Получить элемент отгрузки по ID"""
        item = await self.items_repo.get(item_id)
        if not item:
            return None
        
        return ShipmentItemDetailResponse(
            id=item.id,
            shipment_id=item.shipment_id,
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            ordered_quantity=item.ordered_quantity,
            fact_quantity=item.fact_quantity,
            created_at=item.created_at
        )
    
    async def delete_shipment(self, shipment_id: str) -> bool:
        try:
            await self.items_repo.delete_by_shipment_id(shipment_id)
            return await self.repo.delete(shipment_id)
        except Exception:
            return False

    async def delete_shipment_item(self, item_id: str) -> bool:
        return await self.items_repo.delete(item_id)
