from uuid import uuid4
from backend.domain.errors import InvalidOperation, NotFound, Conflict
from backend.ports import WarehouseRepository, Transaction
from backend.schemas.warehouse import WarehouseCreate, WarehouseUpdate


class WarehouseService:
    def __init__(self, repo: WarehouseRepository, transaction: Transaction):
        self.repo = repo
        self.transaction = transaction

    async def create_warehouse(self, data: WarehouseCreate):
        async with self.transaction:
            if await self.repo.get_by_name(data.name) is not None:
                raise Conflict(f"Склад с именем '{data.name}' уже существует.")
            warehouse = await self.repo.create(id=str(uuid4()), **data.model_dump())
            await self.transaction.commit()
            return warehouse

    async def get_warehouse(self, warehouse_id: str):
        warehouse = await self.repo.get_by_id(warehouse_id)
        if warehouse is None:
            raise NotFound(f"Склад '{warehouse_id}' не найден.")
        return warehouse

    async def edit_warehouse(self, warehouse_id: str, data: WarehouseUpdate):
        async with self.transaction:
            locked = await self.repo.lock_many([warehouse_id])
            if not locked:
                raise NotFound(f"Склад '{warehouse_id}' не найден.")
            if (
                data.max_products is not None
                and data.max_products < locked[0].products_count
            ):
                raise InvalidOperation(
                    "Вместимость не может быть меньше текущего количества товаров."
                )
            if data.name and data.name != locked[0].name:
                existing = await self.repo.get_by_name(data.name)
                if existing is not None:
                    raise Conflict(f"Склад с именем '{data.name}' уже существует.")
            warehouse = await self.repo.edit_by_id(
                warehouse_id, **data.model_dump(exclude_unset=True)
            )
            await self.transaction.commit()
            return warehouse

    async def delete_warehouse(self, warehouse_id: str) -> dict:
        async with self.transaction:
            await self.repo.delete(warehouse_id)
            await self.transaction.commit()
        return {"detail": f"Склад с id '{warehouse_id}' успешно удалён."}

    async def get_warehouses(self, *, limit: int = 100, offset: int = 0):
        return await self.repo.get_all(
            limit=min(max(limit, 1), 500), offset=max(offset, 0)
        )
