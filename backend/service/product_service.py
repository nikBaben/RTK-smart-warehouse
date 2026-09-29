from uuid import uuid4

from backend.domain.errors import InvalidOperation, NotFound
from backend.ports import ProductRepository, WarehouseRepository, Transaction
from backend.schemas.product import ProductCreate, ProductEdit


class ProductService:
    def __init__(
        self,
        repo: ProductRepository,
        warehouses: WarehouseRepository,
        transaction: Transaction,
    ):
        self.repo = repo
        self.warehouses = warehouses
        self.transaction = transaction

    async def _adjust_stock(self, changes: dict[str, int]) -> None:
        warehouses = {w.id: w for w in await self.warehouses.lock_many(sorted(changes))}
        for warehouse_id, delta in changes.items():
            warehouse = warehouses.get(warehouse_id)
            if warehouse is None:
                raise NotFound(f"Склад '{warehouse_id}' не найден.")
            count = warehouse.products_count + delta
            if count < 0:
                raise InvalidOperation(
                    "Количество товаров на складе несогласовано с остатками."
                )
            if (
                delta > 0
                and warehouse.max_products is not None
                and count > warehouse.max_products
            ):
                available = max(warehouse.max_products - warehouse.products_count, 0)
                raise InvalidOperation(
                    f"Склад '{warehouse_id}' переполнен. Можно добавить только {available} товаров."
                )
        # Validate every warehouse before changing any counters.
        for warehouse_id, delta in changes.items():
            await self.warehouses.set_products_count(
                warehouse_id, warehouses[warehouse_id].products_count + delta
            )

    async def create_product(self, data: ProductCreate):
        if not data.warehouse_id:
            raise InvalidOperation("warehouse_id is required")
        async with self.transaction:
            await self._adjust_stock({data.warehouse_id: data.stock})
            product = await self.repo.create(
                id=str(uuid4()),
                name=data.name,
                category=data.category,
                article=data.article,
                stock=data.stock,
                min_stock=int(data.stock * 0.2),
                optimal_stock=int(data.stock * 0.8),
                current_zone="A",
                current_row=data.current_row,
                current_shelf=data.current_shelf,
                warehouse_id=data.warehouse_id,
            )
            await self.transaction.commit()
            return product

    async def edit_product(self, product_id: str, data: ProductEdit):
        async with self.transaction:
            product = await self.repo.get_for_update(product_id)
            if product is None:
                raise NotFound(f"Товар '{product_id}' не найден.")
            values = data.model_dump(exclude_unset=True, exclude_none=True)
            target = values.get("warehouse_id", product.warehouse_id)
            stock = values.get("stock", product.stock)
            changes = {product.warehouse_id: -product.stock}
            changes[target] = changes.get(target, 0) + stock
            await self._adjust_stock(changes)
            updated = await self.repo.edit(product_id, **values)
            await self.transaction.commit()
            return updated

    async def delete_product(self, product_id: str) -> dict:
        async with self.transaction:
            product = await self.repo.get_for_update(product_id)
            if product is None:
                raise NotFound(f"Товар '{product_id}' не найден.")
            await self._adjust_stock({product.warehouse_id: -product.stock})
            await self.repo.delete(product_id)
            await self.transaction.commit()
        return {"detail": f"Товар с id '{product_id}' успешно удалён."}

    async def get_products_by_warehouse_id(self, warehouse_id: str):
        return await self.repo.get_all_by_warehouse_id(warehouse_id)
