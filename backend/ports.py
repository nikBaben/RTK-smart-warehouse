"""Small structural interfaces used by services. No database or web framework imports."""

from __future__ import annotations
from typing import Protocol, Optional, List, Dict, Any, Tuple, Sequence
from datetime import datetime
from backend.domain.entities import (
    Alarm,
    Delivery,
    DeliveryItems,
    InventoryHistory,
    KeycloakUser,
    Product,
    Robot,
    ScheduledDelivery,
    Shipment,
    ShipmentItems,
    User,
    Warehouse,
)
from backend.domain.enums import DeliveryStatus
from backend.schemas.user import UserCreate


class Transaction(Protocol):
    async def __aenter__(self) -> Transaction: ...
    async def commit(self) -> None: ...
    async def __aexit__(self, exc_type, exc, traceback) -> bool: ...


class AlarmRepository(Protocol):
    async def create(self, *, id: str, user_id: int, message: str) -> Alarm: ...

    async def get(self, user_id: int) -> list[Alarm]: ...

    async def delete(self, user_id: int): ...


class DeliveryItemsRepository(Protocol):
    async def create(
        self,
        *,
        id: str,
        delivery_id: Optional[str],
        product_id: Optional[str],
        warehouse_id: Optional[str],
        ordered_quantity: int,
        fact_quantity: int,
    ) -> DeliveryItems: ...

    async def get(self, id: str) -> Optional[DeliveryItems]: ...

    async def get_by_delivery_id(self, delivery_id: str) -> List[DeliveryItems]: ...

    async def delete(self, id: str) -> bool: ...

    async def delete_by_delivery_id(self, delivery_id: str) -> bool: ...


class DeliveryRepository(Protocol):
    async def create(
        self,
        *,
        id: str,
        warehouse_id: Optional[str],
        scheduled_at,
        quantity: int,
        delivered_at,
        name: Optional[str] = None,
        status: Optional[DeliveryStatus] = DeliveryStatus.scheduled,
        supplier: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Delivery: ...

    async def get(self, id: str) -> Optional[Delivery]: ...

    async def mark_arrived(self, id: str) -> Optional[Delivery]: ...

    async def delete(self, id: str) -> bool: ...


class InventoryHistoryRepository(Protocol):
    async def get_all_by_warehouse_id(
        self, warehouse_id: str
    ) -> List[InventoryHistory]: ...

    async def get_filtered_inventory_history(
        self,
        warehouse_id: str,
        filters: Dict[str, Any],
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[Tuple[InventoryHistory, Optional[int], int]], int]: ...

    async def inventory_history_create_graph(
        self, warehouse_id: str, record_ids: List[str]
    ) -> Dict[str, List[Tuple[datetime, int]]]: ...

    async def inventory_history_unique_zones(self, warehouse_id: str) -> List[str]: ...

    async def inventory_history_unique_categories(
        self, warehouse_id: str
    ) -> List[str]: ...

    async def get_export_rows(self, warehouse_id: str, record_ids: list[str]): ...

    async def get_warehouse_name(self, warehouse_id: str) -> str | None: ...

    async def find_product(
        self, warehouse_id: str, reference: str
    ) -> Product | None: ...

    async def add_records(self, rows: list[dict]) -> None: ...


class KkidUserRepository(Protocol):
    async def create(self, kkid: str, user_id: int) -> KeycloakUser: ...


class OperationsRepository(Protocol):
    async def get_all_deliveries_by_warehouse(
        self, warehouse_id: str
    ) -> List[Delivery]: ...

    async def get_all_shipments_by_warehouse(
        self, warehouse_id: str
    ) -> List[Shipment]: ...

    async def get_all_operations_by_warehouse(
        self, warehouse_id: str
    ) -> Tuple[List[Delivery], List[Shipment]]: ...


class PredictRepository(Protocol):
    async def get_top5_soon_depleted(self, warehouse_id: str): ...

    async def save_predictions(self, results: List[Tuple]): ...


class ProductRepository(Protocol):
    async def get_all_by_warehouse_id(self, warehouse_id: str) -> List[Product]: ...

    async def get(self, id: str) -> Optional[Product]: ...

    async def get_name(self, product_id: str) -> Optional[str]: ...

    async def required_delivery(self, product_id: str) -> Optional[int]: ...

    async def get_stock(self, product_id: str) -> Optional[int]: ...

    async def create(self, **values) -> Product: ...

    async def get_for_update(self, product_id: str) -> Optional[Product]: ...

    async def edit(self, id: str, **values) -> Product: ...

    async def delete(self, id: str) -> None: ...

    async def list_ids(self, warehouse_id: str) -> list[str]: ...


class ReportsRepository(Protocol):
    async def get_operations_by_year_and_warehouse(
        self, year: int, warehouse_id: str
    ) -> Tuple[List[Delivery], List[Shipment]]: ...


class RobotRepository(Protocol):
    async def create(
        self,
        *,
        id: str,
        status: str,
        battery_level: int,
        current_zone: str,
        current_row: int,
        current_shelf: str,
        warehouse_id: str,
    ) -> Robot: ...

    async def get(self, id: str) -> Optional[Robot]: ...

    async def get_all_by_warehouse_id(self, warehouse_id: str) -> Sequence[Robot]: ...

    async def delete(self, id: str) -> None: ...


class ScheduledDeliveryRepository(Protocol):
    async def get(self, id: str) -> ScheduledDelivery | None: ...

    async def create(self, **values) -> ScheduledDelivery: ...


class ShipmentItemsRepository(Protocol):
    async def create(
        self,
        *,
        id: str,
        shipment_id: Optional[str],
        product_id: Optional[str],
        warehouse_id: Optional[str],
        ordered_quantity: int,
        fact_quantity: int,
    ) -> ShipmentItems: ...

    async def get(self, id: str) -> Optional[ShipmentItems]: ...

    async def get_by_shipment_id(self, shipment_id: str) -> List[ShipmentItems]: ...

    async def delete(self, id: str) -> bool: ...

    async def delete_by_shipment_id(self, shipment_id: str) -> bool: ...


class ShipmentRepository(Protocol):
    async def create(
        self,
        *,
        id: str,
        warehouse_id: Optional[str],
        name: Optional[str],
        scheduled_at,
        shipped_at: Optional[object],
        quantity: int,
        status: Optional[object],
        customer: Optional[str],
        notes: Optional[str],
    ) -> Shipment: ...

    async def get(self, id: str) -> Optional[Shipment]: ...

    async def delete(self, id: str) -> bool: ...


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> Optional[User]: ...

    async def get_by_kkid(self, kkid: str) -> Optional[User]: ...

    async def get_by_id(self, user_id: int) -> Optional[User]: ...

    async def create(self, user_create: UserCreate) -> User: ...

    async def update(self, user_id: int, update_data: dict) -> Optional[User]: ...


class WarehouseRepository(Protocol):
    async def get_by_name(self, name: str) -> Warehouse | None: ...

    async def create(
        self, *, id: str, name: str, address: str, max_products: int
    ) -> Warehouse: ...

    async def get_by_id(self, warehouse_id: str) -> Warehouse | None: ...

    async def edit_by_id(
        self,
        id: str,
        *,
        name: str | None = None,
        address: str | None = None,
        max_products: int | None = None,
    ) -> Warehouse: ...

    async def delete(self, id: str): ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Warehouse]: ...

    async def list_ids(self) -> list[str]: ...

    async def lock_many(self, warehouse_ids: list[str]) -> list[Warehouse]: ...

    async def set_products_count(self, warehouse_id: str, count: int) -> None: ...


class IdentityProvider(Protocol):
    async def create_user(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        username: str,
    ) -> str: ...
    async def delete_user(self, user_id: str) -> bool: ...
    async def login(self, email: str, password: str) -> dict: ...
    async def get_user_info(self, token: str) -> dict: ...
    async def refresh_token(self, refresh_token: str) -> dict: ...
    async def logout(self, refresh_token: str) -> bool: ...
    async def get_identity_from_token(self, access_token: str) -> dict: ...


class DepletionPredictor(Protocol):
    async def predict_depletion_with_confidence(
        self, *, product_id: str, warehouse_id: str, horizon_days: int, as_of: datetime
    ) -> tuple: ...


class PredictorFactory(Protocol):
    def __call__(self, *, model_path: str) -> DepletionPredictor: ...
