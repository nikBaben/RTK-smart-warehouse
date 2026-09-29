from uuid import uuid4
from backend.domain.errors import NotFound
from backend.ports import DeliveryRepository, DeliveryItemsRepository, Transaction
from backend.schemas.delivery import DeliveryCreate
from backend.schemas.delivery_items import DeliveryItemsCreate


class DeliveryService:
    def __init__(
        self,
        repo: DeliveryRepository,
        items_repo: DeliveryItemsRepository,
        transaction: Transaction,
    ):
        self.repo = repo
        self.items_repo = items_repo
        self.transaction = transaction

    async def create_delivery(self, data: DeliveryCreate):
        async with self.transaction:
            values = data.model_dump()
            values["id"] = data.id or str(uuid4())
            result = await self.repo.create(**values)
            await self.transaction.commit()
            return result

    async def add_item(self, data: DeliveryItemsCreate):
        async with self.transaction:
            values = data.model_dump()
            values["id"] = data.id or str(uuid4())
            result = await self.items_repo.create(**values)
            await self.transaction.commit()
            return result

    async def get_delivery_by_id(self, delivery_id: str):
        return await self.repo.get(delivery_id)

    async def get_delivery_items(self, delivery_id: str):
        return await self.items_repo.get_by_delivery_id(delivery_id)

    async def get_delivery_item_by_id(self, item_id: str):
        return await self.items_repo.get(item_id)

    async def delete_delivery(self, delivery_id: str) -> bool:
        async with self.transaction:
            if await self.repo.get(delivery_id) is None:
                raise NotFound("Delivery not found")
            await self.items_repo.delete_by_delivery_id(delivery_id)
            deleted = await self.repo.delete(delivery_id)
            if not deleted:
                raise NotFound("Delivery not found")
            await self.transaction.commit()
            return True

    async def delete_delivery_item(self, item_id: str) -> bool:
        async with self.transaction:
            deleted = await self.items_repo.delete(item_id)
            if not deleted:
                raise NotFound("Delivery item not found")
            await self.transaction.commit()
            return True

    async def get(self, id: str):
        return await self.repo.get(id)

    async def mark_arrived(self, id: str):
        async with self.transaction:
            delivery = await self.repo.mark_arrived(id)
            if delivery is None:
                raise NotFound("Delivery not found")
            await self.transaction.commit()
            return delivery
