"""Storage-independent record shapes returned by repository adapters."""

from __future__ import annotations
from typing import Protocol, Optional
from datetime import datetime
from backend.domain.enums import DeliveryStatus, ShipmentStatus


class Delivery(Protocol):
    id: str
    name: Optional[str]
    warehouse_id: Optional[str]
    scheduled_at: datetime
    delivered_at: Optional[datetime]
    quantity: int
    status: DeliveryStatus
    supplier: Optional[str]
    notes: Optional[str]
    created_at: datetime


class ScheduledDelivery(Protocol):
    id: str
    product_id: Optional[str]
    warehouse_id: Optional[str]
    scheduled_at: datetime
    quantity: int
    status: str
    supplier: Optional[str]
    notes: Optional[str]
    created_at: datetime


class DeliveryItems(Protocol):
    id: str
    delivery_id: Optional[str]
    product_id: Optional[str]
    warehouse_id: Optional[str]
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime


class Warehouse(Protocol):
    id: str
    name: str
    address: str
    max_products: int
    row_x: int
    row_y: int
    products_count: int
    created_at: datetime


class RobotHistory(Protocol):
    id: str
    robot_id: str | None
    warehouse_id: str
    status: str
    created_at: datetime


class Product(Protocol):
    id: str
    name: str
    category: Optional[str]
    article: Optional[str]
    stock: int
    min_stock: int
    optimal_stock: int
    current_zone: str
    current_row: int
    current_shelf: str
    status: str
    last_scanned_at: Optional[datetime]
    warehouse_id: str
    created_at: datetime


class Robot(Protocol):
    id: str
    status: str
    battery_level: int
    last_update: datetime
    current_zone: str
    current_row: int
    current_shelf: int
    warehouse_id: str
    created_at: datetime


class InventoryHistory(Protocol):
    id: str
    product_id: Optional[str]
    robot_id: Optional[str]
    warehouse_id: str
    current_zone: str
    current_row: int
    current_shelf: str
    name: Optional[str]
    category: Optional[str]
    article: Optional[str]
    stock: Optional[int]
    min_stock: Optional[int]
    optimal_stock: Optional[int]
    status: Optional[str]
    created_at: datetime


class Shipment(Protocol):
    id: str
    name: Optional[str]
    warehouse_id: str | None
    scheduled_at: datetime
    shipped_at: Optional[datetime]
    quantity: int
    status: ShipmentStatus
    customer: Optional[str]
    notes: Optional[str]
    created_at: datetime


class ShipmentItems(Protocol):
    id: str
    shipment_id: Optional[str]
    product_id: Optional[str]
    warehouse_id: Optional[str]
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime


class User(Protocol):
    id: int
    email: str
    name: str
    role: str
    password_hash: str


class KeycloakUser(Protocol):
    kkid: str
    user_id: int


class Alarm(Protocol):
    id: str
    user_id: int
    message: str
    created_at: datetime
