from pydantic import BaseModel, Field
from typing import Optional
from backend.schemas.product import ProductRead
from backend.schemas.robot import RobotRead


class WarehouseBase(BaseModel):
    name: str = Field(..., max_length=255)
    address: str = Field(..., max_length=255)
    max_products: int = Field(..., ge=0)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseResponse(WarehouseBase):
    id: str
    products_count: int

    model_config = {"from_attributes": True}


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    address: Optional[str] = Field(None, min_length=1)
    max_products: Optional[int] = Field(None, ge=0)
