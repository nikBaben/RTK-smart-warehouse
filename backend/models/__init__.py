"""Register ORM models with SQLAlchemy metadata."""

from .alarm import Alarm
from .delivery import Delivery
from .delivery_items import DeliveryItems
from .inventory_history import InventoryHistory
from .keycloak_user import KeycloakUser
from .predict import PredictAt
from .product import Product
from .robot import Robot
from .robot_history import RobotHistory
from .delivery import ScheduledDelivery
from .shipment import Shipment
from .shipment import ShipmentItems
from .user import User
from .warehouse import Warehouse

__all__ = [
    "Alarm",
    "Delivery",
    "DeliveryItems",
    "InventoryHistory",
    "KeycloakUser",
    "PredictAt",
    "Product",
    "Robot",
    "RobotHistory",
    "ScheduledDelivery",
    "Shipment",
    "ShipmentItems",
    "User",
    "Warehouse",
]
