from sqlalchemy.orm import raiseload
from backend.domain.errors import NotFound
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import noload

from backend.models.warehouse import Warehouse
from backend.models.robot import Robot


class WarehouseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, id: str, name: str, address: str, max_products: int
    ) -> Warehouse:
        warehouse = Warehouse(
            id=id,
            name=name,
            address=address,
            max_products=max_products,
            products_count=0,
        )

        self.session.add(warehouse)
        await self.session.flush()

        await self.session.refresh(warehouse)
        return warehouse

    async def get_by_id(self, warehouse_id: str) -> Warehouse:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        return await self.session.scalar(stmt)

    async def edit_by_id(
        self,
        id: str,
        *,
        name: str | None = None,
        address: str | None = None,
        max_products: int | None = None,
    ) -> Warehouse:
        # Находим склад по id
        warehouse = await self.session.scalar(
            select(Warehouse).where(Warehouse.id == id)
        )
        if not warehouse:
            raise NotFound(f"Склад с id '{id}' не найден.")

        if name is not None:
            warehouse.name = name

        # Обновляем остальные поля
        if address is not None:
            warehouse.address = address

        if max_products is not None:
            warehouse.max_products = max_products

        await self.session.flush()

        await self.session.refresh(warehouse)
        return warehouse

    async def delete(self, id: str):
        warehouse = await self.session.scalar(
            select(Warehouse).where(Warehouse.id == id)
        )

        if not warehouse:
            raise NotFound(f"Склад с id '{id}' не найден.")

        await self.session.delete(warehouse)

        await self.session.flush()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Warehouse]:
        stmt = (
            select(Warehouse)
            .options(
                noload(Warehouse.products),
                noload(Warehouse.robots),
                noload(Warehouse.inventory_history),
            )
            .order_by(Warehouse.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_ids(self) -> list[str]:
        stmt = select(Warehouse.id)
        return (await self.session.execute(stmt)).scalars().all()

    # Склады, где есть хотя бы один робот (для шардера/раннера)
    async def ids_having_robots(self) -> List[str]:
        rows = await self.session.execute(
            select(Warehouse.id)
            .join(Robot, Robot.warehouse_id == Warehouse.id)
            .group_by(Warehouse.id)
        )
        return [wid for (wid,) in rows.all() if wid]

    async def lock_many(self, warehouse_ids: list[str]) -> list[Warehouse]:
        # Deterministic lock order prevents opposite transfers from deadlocking.
        result = await self.session.scalars(
            select(Warehouse)
            .options(raiseload("*"))
            .where(Warehouse.id.in_(warehouse_ids))
            .order_by(Warehouse.id)
            .with_for_update()
        )
        return list(result.all())

    async def set_products_count(self, warehouse_id: str, count: int) -> None:
        from sqlalchemy import update

        await self.session.execute(
            update(Warehouse)
            .where(Warehouse.id == warehouse_id)
            .values(products_count=count)
        )

    async def get_by_name(self, name: str) -> Warehouse | None:
        return await self.session.scalar(
            select(Warehouse).where(Warehouse.name == name)
        )
