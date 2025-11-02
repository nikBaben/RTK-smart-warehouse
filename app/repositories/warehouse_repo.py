from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload,noload
from sqlalchemy.exc import IntegrityError

from app.models.warehouse import Warehouse


class WarehouseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        id: str,
        name: str,
        address: str,
        max_products: int
    ) -> Warehouse:
        existing_warehouse = await self.session.scalar(
            select(Warehouse).where(Warehouse.name == name)
        )
        if existing_warehouse:
            raise ValueError(f"Склад с именем '{name}' уже существует.")

        warehouse = Warehouse(
            id=id,
            name=name,
            address=address,
            max_products = max_products,
            products_count = 0
        )

        self.session.add(warehouse)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        await self.session.refresh(warehouse)
        return warehouse
    
    async def get_by_id(self, warehouse_id: str) -> Warehouse:
        stmt = (
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        return await self.session.scalar(stmt)
    
    async def edit_by_id(
        self,
        id: str,
        *,
        name: str | None = None,
        address: str | None = None,
        max_products: int | None = None
    ) -> Warehouse:
    # Находим склад по id
        warehouse = await self.session.scalar(
            select(Warehouse).where(Warehouse.id == id)
        )
        if not warehouse:
            raise ValueError(f"Склад с id '{id}' не найден.")

        # Проверяем, если нужно изменить имя — чтобы не было дублей
        if name and name != warehouse.name:
            existing_warehouse = await self.session.scalar(
                select(Warehouse).where(Warehouse.name == name)
            )
            if existing_warehouse:
                raise ValueError(f"Склад с именем '{name}' уже существует.")
            warehouse.name = name

        # Обновляем остальные поля
        if address is not None:
            warehouse.address = address

        if max_products is not None:
            warehouse.max_products = max_products

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        await self.session.refresh(warehouse)
        return warehouse
    
    async def delete(self, id: str):
        warehouse = await self.session.scalar(
            select(Warehouse).where(Warehouse.id == id)
        )

        if not warehouse:
            raise ValueError(f"Склад с id '{id}' не найден.")

        await self.session.delete(warehouse)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Warehouse]:
        stmt = (
        select(Warehouse)
        .options(
            noload(Warehouse.products),
            noload(Warehouse.robots),
            noload(Warehouse.inventory_history),
        )
        .order_by(Warehouse.id)            # детерминированность + индекс по PK
        .limit(limit)
        .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_ids(self) -> list[str]:
        stmt = select(Warehouse.id)
        return (await self.session.execute(stmt)).scalars().all()