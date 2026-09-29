from uuid import uuid4
from backend.domain.errors import NotFound
from backend.ports import ShipmentRepository, ShipmentItemsRepository, Transaction
from backend.schemas.shipment import ShipmentCreate
from backend.schemas.shipment_items import ShipmentItemsCreate


class ShipmentService:
    def __init__(
        self,
        repo: ShipmentRepository,
        items_repo: ShipmentItemsRepository,
        transaction: Transaction,
    ):
        self.repo = repo
        self.items_repo = items_repo
        self.transaction = transaction

    async def create_shipment(self, data: ShipmentCreate):
        async with self.transaction:
            values = data.model_dump()
            values["id"] = data.id or str(uuid4())
            result = await self.repo.create(**values)
            await self.transaction.commit()
            return result

    async def add_item(self, data: ShipmentItemsCreate):
        async with self.transaction:
            values = data.model_dump()
            values["id"] = data.id or str(uuid4())
            result = await self.items_repo.create(**values)
            await self.transaction.commit()
            return result

    async def get_shipment_by_id(self, shipment_id: str):
        return await self.repo.get(shipment_id)

    async def get_shipment_items(self, shipment_id: str):
        return await self.items_repo.get_by_shipment_id(shipment_id)

    async def get_shipment_item_by_id(self, item_id: str):
        return await self.items_repo.get(item_id)

    async def delete_shipment(self, shipment_id: str) -> bool:
        async with self.transaction:
            if await self.repo.get(shipment_id) is None:
                raise NotFound("Shipment not found")
            await self.items_repo.delete_by_shipment_id(shipment_id)
            deleted = await self.repo.delete(shipment_id)
            if not deleted:
                raise NotFound("Shipment not found")
            await self.transaction.commit()
            return True

    async def delete_shipment_item(self, item_id: str) -> bool:
        async with self.transaction:
            deleted = await self.items_repo.delete(item_id)
            if not deleted:
                raise NotFound("Shipment item not found")
            await self.transaction.commit()
            return True
