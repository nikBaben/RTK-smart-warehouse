from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.enums import DeliveryStatus, ShipmentStatus


class DeliveryShortResponse(BaseModel):
    id: str
    name: Optional[str]
    supplier: Optional[str]
    scheduled_at: datetime
    quantity: int
    status: DeliveryStatus
    warehouse_id: Optional[str]
    
    class Config:
        from_attributes = True


class ShipmentShortResponse(BaseModel):
    id: str
    name: Optional[str]
    customer: Optional[str]
    scheduled_at: datetime
    quantity: int
    status: ShipmentStatus
    warehouse_id: Optional[str]
    
    class Config:
        from_attributes = True

class DeliveryDetailResponse(BaseModel):
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
    
    class Config:
        from_attributes = True


class DeliveryItemDetailResponse(BaseModel):
    id: str
    delivery_id: Optional[str]
    product_id: Optional[str]
    warehouse_id: Optional[str]
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ShipmentDetailResponse(BaseModel):
    id: str
    name: Optional[str]
    warehouse_id: Optional[str]
    scheduled_at: datetime
    shipped_at: Optional[datetime]
    quantity: int
    status: ShipmentStatus
    customer: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ShipmentItemDetailResponse(BaseModel):
    id: str
    shipment_id: Optional[str]
    product_id: Optional[str]
    warehouse_id: Optional[str]
    ordered_quantity: int
    fact_quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AllOperationsResponse(BaseModel):
    deliveries: List[DeliveryShortResponse]
    shipments: List[ShipmentShortResponse]