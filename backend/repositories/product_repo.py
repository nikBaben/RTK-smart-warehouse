from sqlalchemy.orm import raiseload
from backend.domain.errors import NotFound
from typing import Optional, List, Dict, Iterable, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, noload
from sqlalchemy import select, func, update, distinct, case, tuple_, text

from backend.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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

    # Проверка, что на складе достаточно места для добавления указанного количества товаров.
    # Если в БД нет данных о лимите/счётчике — спокойно выходим (не ограничиваем).

    async def get_name(self, product_id: str) -> Optional[str]:
        res = await self.session.execute(
            text("SELECT name FROM products WHERE id = :pid"),
            {"pid": product_id},
        )
        row = res.first()
        return row[0] if row else None

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
        await self.session.flush()
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

    async def mark_last_scanned(
        self, product_ids: Iterable[str], when: datetime
    ) -> None:
        ids = list(set(product_ids))
        if not ids:
            return
        await self.session.execute(
            update(Product).where(Product.id.in_(ids)).values(last_scanned_at=when)
        )
        await self.session.flush()

    async def min_scan_seed_rows(
        self, warehouse_id: str
    ) -> List[Tuple[int, str, datetime]]:
        rows = await self.session.execute(
            select(
                Product.current_row,
                func.upper(func.trim(Product.current_shelf)),
                func.min(
                    func.coalesce(Product.last_scanned_at, func.to_timestamp(0))
                ).label("min_scan"),
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
                tuple_(
                    Product.current_row, func.upper(func.trim(Product.current_shelf))
                ).in_(row_shelf_pairs),
                (Product.last_scanned_at.is_(None))
                | (Product.last_scanned_at < cutoff),
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
                func.min(
                    func.coalesce(Product.last_scanned_at, func.to_timestamp(0))
                ).label("min_scan"),
            )
            .where(
                Product.warehouse_id == warehouse_id,
                func.upper(func.trim(Product.current_shelf)) != "0",
                (Product.last_scanned_at.is_(None))
                | (Product.last_scanned_at < cutoff),
            )
            .group_by(Product.current_row, func.upper(func.trim(Product.current_shelf)))
            .order_by(
                func.min(
                    func.coalesce(Product.last_scanned_at, func.to_timestamp(0))
                ).asc()
            )
        )
        return [(int(r), str(s), ms) for r, s, ms in rows.all()]

    async def eligible_products_in_cell(
        self,
        warehouse_id: str,
        shelf_num: int,
        row_num: int,
        cutoff: datetime,
    ) -> List[Product]:
        shelf_str = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[max(0, min(25, shelf_num - 1))]
            if shelf_num > 0
            else "0"
        )
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
                (Product.last_scanned_at.is_(None))
                | (Product.last_scanned_at < cutoff),
            )
        )
        return list(res.scalars().all())

    async def create(self, **values) -> Product:
        product = Product(**values)
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def get_for_update(self, product_id: str) -> Optional[Product]:
        return await self.session.scalar(
            select(Product)
            .options(raiseload("*"))
            .where(Product.id == product_id)
            .with_for_update(of=Product)
        )

    async def edit(self, id: str, **values) -> Product:
        product = await self.get(id)
        if product is None:
            raise NotFound(f"Товар '{id}' не найден.")
        for key, value in values.items():
            setattr(product, key, value)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete(self, id: str) -> None:
        product = await self.get(id)
        if product is None:
            raise NotFound(f"Товар '{id}' не найден.")
        await self.session.delete(product)
        await self.session.flush()

    async def list_ids(self, warehouse_id: str) -> list[str]:
        return list(
            (
                await self.session.scalars(
                    select(Product.id).where(Product.warehouse_id == warehouse_id)
                )
            ).all()
        )
