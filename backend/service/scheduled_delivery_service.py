from backend.domain.errors import Conflict, InvalidOperation, NotFound
from backend.ports import (
    ScheduledDeliveryRepository,
    ProductRepository,
    WarehouseRepository,
    Transaction,
)
from backend.schemas.scheduled_delivery import ScheduledDeliveryIn


class ScheduledDeliveryService:
    def __init__(
        self,
        repo: ScheduledDeliveryRepository,
        products: ProductRepository,
        warehouses: WarehouseRepository,
        transaction: Transaction,
    ):
        self.repo = repo
        self.products = products
        self.warehouses = warehouses
        self.transaction = transaction

    @staticmethod
    def _check_retry(existing, data):
        fields = (
            "product_id",
            "warehouse_id",
            "scheduled_at",
            "quantity",
            "supplier",
            "notes",
        )
        if any(getattr(existing, field) != getattr(data, field) for field in fields):
            raise Conflict("Этот ID плана уже используется с другими параметрами.")
        return existing

    async def create(self, data: ScheduledDeliveryIn):
        try:
            async with self.transaction:
                existing = await self.repo.get(data.id)
                if existing is not None:
                    self._check_retry(existing, data)
                    await self.transaction.commit()
                    return existing
                product = await self.products.get(data.product_id)
                if product is None:
                    raise NotFound("Product not found")
                if await self.warehouses.get_by_id(data.warehouse_id) is None:
                    raise NotFound("Warehouse not found")
                if product.warehouse_id != data.warehouse_id:
                    raise InvalidOperation("Товар относится к другому складу.")
                delivery = await self.repo.create(**data.model_dump())
                await self.transaction.commit()
                return delivery
        except Conflict:
            # A concurrent retry may have inserted the same ID. The adapter has rolled back.
            existing = await self.repo.get(data.id)
            if existing is None:
                raise
            return self._check_retry(existing, data)
