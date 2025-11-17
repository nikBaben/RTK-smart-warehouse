from typing import Optional, List, Dict, Iterable, Tuple
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, noload
from sqlalchemy import select, func, update, distinct, case, tuple_, text
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

        await self.check_limit(warehouse_id, stock)

        product = Product(
            id=id,
            name=name,
            category=category,
            article=article,
            stock=stock,
            min_stock=stock * 0.2,
            optimal_stock=stock * 0.8,
            current_zone=current_zone,
            current_row=current_row,
            current_shelf=current_shelf,
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

    async def get_all_by_warehouse_id(self, warehouse_id: str) -> List[Product]:
        stmt = (
            select(Product)
            .where(Product.warehouse_id == warehouse_id)
            .options(
                load_only(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.article,
                    Product.stock,
                    Product.min_stock,
                    Product.optimal_stock,
                    Product.current_zone,
                    Product.current_row,
                    Product.current_shelf,
                    Product.status,
                    Product.warehouse_id,
                    Product.last_scanned_at,
                    Product.created_at,  
                ),

                noload(Product.warehouse),
                noload(Product.history),
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get(self, id: str) -> Optional[Product]:
        return await self.session.scalar(select(Product).where(Product.id == id))

    async def edit(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        article: Optional[str] = None,
        stock: Optional[int] = None,
        category: Optional[str] = None,
        current_row: Optional[int] = None,
        current_shelf: Optional[str] = None,
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

        # корректно обрабатываем изменение стока
        if stock is not None and stock != old_stock:
            # сначала снимаем старое количество с прежнего склада
            await self.bump_products_count(old_wh, -old_stock)
            # проверяем лимит на целевом складе (вдруг перенесли)
            target_wh = new_wh
            await self.check_limit(target_wh, stock)
            # добавляем новое количество на целевой склад
            await self.bump_products_count(target_wh, +stock)

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
    ) -> List[Product]:
        stmt = select(Product)
        if warehouse_id:
            stmt = stmt.where(Product.warehouse_id == warehouse_id)
        if name_query:
            stmt = stmt.where(func.lower(Product.name).like(f"%{name_query.lower()}%"))

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, id: str) -> None:
        product = await self.session.scalar(select(Product).where(Product.id == id))
        
        if not product:
            raise ValueError(f"Товар с id '{id}' не найден.")

        await self.bump_products_count(product.warehouse_id, -product.stock)
        await self.session.delete(product)
        
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    #Проверка, что на складе достаточно места для добавления указанного количества товаров.
    #Если в БД нет данных о лимите/счётчике — спокойно выходим (не ограничиваем).
    async def check_limit(self, warehouse_id: str, stock: int) -> None:
        result = await self.session.execute(
            select(Warehouse.max_products, Warehouse.products_count)
            .where(Warehouse.id == warehouse_id)
        )
        row = result.one_or_none()
        if not row:
            return
        limit, products_count = row
        if limit is None or products_count is None:
            return
        allow = max(limit - products_count, 0)
        if stock > allow:
            raise HTTPException(
                status_code=400,
                detail=f"Склад '{warehouse_id}' переполнен. Можно добавить только {allow} товаров.",
            )

    async def get_name(self, product_id: str) -> Optional[str]:
        res = await self.session.execute(
            text("SELECT name FROM products WHERE id = :pid"),
            {"pid": product_id},
        )
        row = res.first()
        return row[0] if row else None
    
    async def get_nam(self, product_id: str) -> Optional[str]:
        """
        Возвращает имя товара по product_id.
        Если товара нет — возвращает None.
        """
        stmt = select(Product.name).where(Product.id == product_id)

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        return row

    async def required_delivery(self, product_id: str) -> Optional[int]:
        result = await self.session.execute(
            select(Product.stock, Product.optimal_stock).where(Product.id == product_id)
        )
        row = result.one_or_none()
        if not row:
            return None

        stock, optimal_stock = row
        required = max((optimal_stock or 0) - (stock or 0), 0)
        return int(required)

    async def get_stock(self, product_id: str) -> Optional[int]:
        result = await self.session.execute(
            select(Product.stock).where(Product.id == product_id)
        )
        row = result.one_or_none()
        return int(row[0]) if row and row[0] is not None else None

    async def bump_products_count(self, warehouse_id: str, delta: int) -> None:
        if not warehouse_id:
            return
        stmt = (
            update(Warehouse)
            .where(Warehouse.id == warehouse_id)
            .values(products_count=func.greatest(Warehouse.products_count + delta, 0))
        )
        await self.session.execute(stmt)

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(Product.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    async def recompute_statuses_for_warehouse(self, warehouse_id: str) -> int:
        min_thr = func.coalesce(Product.min_stock, -1)
        opt_thr = func.coalesce(Product.optimal_stock, -1)

        status_case = case(
            (Product.stock < min_thr, "critical"),
            (Product.stock < opt_thr, "low"),
            else_="ok",
        )

        stmt = (
            update(Product)
            .where(Product.warehouse_id == warehouse_id)
            .values(status=status_case)
            .execution_options(synchronize_session=False)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

    async def get_avg_stock_by_status(self, warehouse_id: str) -> Dict[str, float]:
        stmt = (
            select(
                func.lower(Product.status).label("status"),
                func.avg(Product.stock).label("avg_stock"),
            )
            .where(Product.warehouse_id == warehouse_id)
            .where(Product.status.is_not(None))
            .where(func.length(func.trim(Product.status)) > 0)
            .where(Product.stock.is_not(None))
            .group_by(func.lower(Product.status))
        )
        rows = (await self.session.execute(stmt)).all()
        return {status: round(float(avg or 0.0), 2) for status, avg in rows}

    async def get_all_by_warehouse_id_light(self, warehouse_id: str) -> List[Product]:
        res = await self.session.execute(
            select(Product)
            .options(
                load_only(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.article,
                    Product.stock,
                    Product.min_stock,
                    Product.optimal_stock,
                    Product.current_zone,
                    Product.current_row,
                    Product.current_shelf,
                    Product.status,
                    Product.warehouse_id,
                    Product.last_scanned_at,
                    Product.created_at,  
                ),
                noload(Product.warehouse),
                noload(Product.history),
            )
            .where(Product.warehouse_id == warehouse_id)
        )
        return list(res.scalars().all())

    async def mark_last_scanned(self, product_ids: Iterable[str], when: datetime) -> None:
        ids = list(set(product_ids))
        if not ids:
            return
        await self.session.execute(
            update(Product).where(Product.id.in_(ids)).values(last_scanned_at=when)
        )
        await self.session.flush()

    async def min_scan_seed_rows(self, warehouse_id: str) -> List[Tuple[int, str, datetime]]:
        rows = await self.session.execute(
            select(
                Product.current_row,
                func.upper(func.trim(Product.current_shelf)),
                func.min(func.coalesce(Product.last_scanned_at, func.to_timestamp(0))).label("min_scan"),
            )
            .where(
                Product.warehouse_id == warehouse_id,
                func.upper(func.trim(Product.current_shelf)) != "0",
            )
            .group_by(Product.current_row, func.upper(func.trim(Product.current_shelf)))
        )
        return [(int(r), str(s), ms) for r, s, ms in rows.all()]

    async def eligible_cells_by_pairs(
        self,
        warehouse_id: str,
        row_shelf_pairs: List[Tuple[int, str]],
        cutoff: datetime,
    ) -> List[Tuple[int, str]]:
        if not row_shelf_pairs:
            return []
        rows = await self.session.execute(
            select(Product.current_row, func.upper(func.trim(Product.current_shelf)))
            .where(
                Product.warehouse_id == warehouse_id,
                tuple_(Product.current_row, func.upper(func.trim(Product.current_shelf))).in_(row_shelf_pairs),
                (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
            )
            .distinct()
        )
        return [(int(r), str(s)) for r, s in rows.all()]

    async def eligible_cells_fallback(
        self,
        warehouse_id: str,
        cutoff: datetime,
    ) -> List[Tuple[int, str, datetime]]:
        rows = await self.session.execute(
            select(
                Product.current_row,
                func.upper(func.trim(Product.current_shelf)).label("shelf"),
                func.min(func.coalesce(Product.last_scanned_at, func.to_timestamp(0))).label("min_scan"),
            )
            .where(
                Product.warehouse_id == warehouse_id,
                func.upper(func.trim(Product.current_shelf)) != "0",
                (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
            )
            .group_by(Product.current_row, func.upper(func.trim(Product.current_shelf)))
            .order_by(func.min(func.coalesce(Product.last_scanned_at, func.to_timestamp(0))).asc())
        )
        return [(int(r), str(s), ms) for r, s, ms in rows.all()]

    async def eligible_products_in_cell(
        self,
        warehouse_id: str,
        shelf_num: int,
        row_num: int,
        cutoff: datetime,
    ) -> List[Product]:
        shelf_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[max(0, min(25, shelf_num - 1))] if shelf_num > 0 else "0"
        res = await self.session.execute(
            select(Product)
            .options(
                load_only(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.article,
                    Product.stock,
                    Product.min_stock,
                    Product.optimal_stock,
                    Product.current_zone,
                    Product.current_row,
                    Product.current_shelf,
                    Product.created_at, 
                ),
                noload(Product.warehouse),
                noload(Product.history),
            )
            .where(
                Product.warehouse_id == warehouse_id,
                Product.current_row == row_num,
                func.upper(func.trim(Product.current_shelf)) == shelf_str,
                (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
            )
        )
        return list(res.scalars().all())
