from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func,update
from sqlalchemy.exc import IntegrityError

from app.models.product import Product
from app.models.warehouse import Warehouse 


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        id: str,
        name: str,
        category: str,
        article: str,
        stock: int,
        current_zone: str,
        current_row: int,
        current_shelf: str,
        warehouse_id: str,
        check_warehouse_exists: bool = True,
    ) -> Product:
        if check_warehouse_exists:
            exists = await self.session.scalar(
                select(Warehouse.id).where(Warehouse.id == warehouse_id)
            )
            if not exists:
                raise ValueError(f"Склад '{warehouse_id}' не найден")
            
        await self.check_limit(warehouse_id,stock)

        product = Product(
            id=id,
            name=name,
            category=category,
            article = article,
            stock = stock,
            min_stock=stock*0.2,
            optimal_stock=stock* 0.8,
            current_zone =current_zone, 
            current_row = current_row,
            current_shelf = current_shelf,
            warehouse_id=warehouse_id,
        )

        self.session.add(product)
        try:
            await self.session.flush()
            await self.bump_products_count(warehouse_id, +stock)
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
        await self.session.refresh(product)
        return product

    async def get_all_by_warehouse_id(self, warehosue_id: str):
        result = await self.session.execute(
            select(Product).where(Product.warehouse_id == warehosue_id)
        )
        return list(result.scalars().all())


    async def get(self, id: str) -> Optional[Product]:
        return await self.session.scalar(
            select(Product).where(Product.id == id)
        )
    
    async def edit(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        article: Optional[str] = None,
        stock: Optional[int] = None,
        category: Optional[str] = None,
        current_row: Optional[int],
        current_shelf: Optional[str],
        warehouse_id: Optional[str] = None,
        check_warehouse_exists: bool = True,
    ) -> Optional[Product]:
        product = await self.get(id)
        if not product:
            return None

        old_wh = product.warehouse_id
        old_stock = product.stock
        new_wh = old_wh

        if warehouse_id is not None and warehouse_id != old_wh:
            if check_warehouse_exists:
                exists = await self.session.scalar(
                    select(Warehouse.id).where(Warehouse.id == warehouse_id)
                )
            else:
                exists = True
            if not exists:
                raise ValueError(f"Склад '{warehouse_id}' не найден")
            product.warehouse_id = new_wh = warehouse_id

        if stock != old_stock:
            await self.bump_products_count(old_wh,-product.stock)
            await self.check_limit(warehouse_id,stock)
            await self.bump_products_count(old_wh,+stock)
        

        if name is not None:
            product.name = name
        if category is not None:
            product.category = category
        if stock is not None:
            product.stock = stock
        if article is not None:
            product.article = article
        if current_row is not None:
            product.current_row = current_row
        if current_shelf is not None:
            product.current_shelf = current_shelf

        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

        await self.session.refresh(product)
        return product

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        warehouse_id: Optional[str] = None,
        name_query: Optional[str] = None,
    ) -> list[Product]:
        stmt = select(Product)
        if warehouse_id:
            stmt = stmt.where(Product.warehouse_id == warehouse_id)
        if name_query:
            stmt = stmt.where(func.lower(Product.name).like(f"%{name_query.lower()}%"))

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    

    async def delete(self, id: str):
        product = await self.session.scalar(
            select(Product).where(Product.id == id)
        )
        
        if not product:
            raise ValueError(f"Товар с id '{id}' не найден.")

        await self.bump_products_count(product.warehouse_id,-product.stock)
        await self.session.delete(product)
        
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def check_limit(self, warehouse_id:str, stock:int):
        result = await self.session.execute(
            select(Warehouse.max_products, Warehouse.products_count)
            .where(Warehouse.id == warehouse_id)
        )
        limit, products_count = result.one_or_none() or (None, None)
        allow = limit - products_count
        if stock > allow:
            raise HTTPException(
            status_code=400,
            detail=f"Склад '{warehouse_id}' переполнен. Можно добавить только {allow} товаров."
        )
    
    async def get_name(self, product_id: str) -> Optional[str]:
        res = await self.session.execute(
            text("SELECT name FROM products WHERE id = :pid"),
            {"pid": product_id},
        )
        row = res.first()
        return row[0] if row else None
        
    async def bump_products_count(self, warehouse_id: str, delta: int) -> None:
        if not warehouse_id:
            return
        stmt = (
            update(Warehouse)
            .where(Warehouse.id == warehouse_id)
            .values(products_count=func.greatest(Warehouse.products_count + delta, 0))
        )
        await self.session.execute(stmt)
