from enum import Enum


class DeliveryStatus(str, Enum):
    scheduled = "scheduled"
    arrived = "arrived"
    canceled = "canceled"
    rescheduled = "rescheduled"


class ShipmentStatus(str, Enum):
    scheduled = "scheduled"
    shipped = "shipped"
    canceled = "canceled"
    rescheduled = "rescheduled"
