from uuid import uuid4
from typing import Optional
from app.repositories.shipment_repo import ShipmentRepository
from app.repositories.shipment_items_repo import ShipmentItemsRepository
from app.schemas.shipment_items import ShipmentItemsCreate
from app.schemas.shipment import ShipmentCreate


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
