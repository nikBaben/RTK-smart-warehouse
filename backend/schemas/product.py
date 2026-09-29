from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, conint, validator


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Название товара")
    category: str = Field(
        ..., min_length=1, max_length=100, description="Категория товара"
    )
    article: str = Field(
        ..., min_length=1, max_length=100, description="Артикул товара"
    )
    stock: conint(ge=0) = Field(100, description="Всего товаров")  # type: ignore
    current_row: int = 0
    current_shelf: str = "A"


class ProductCreate(ProductBase):
    warehouse_id: Optional[str] = Field(
        None, description="ID склада, к которому привязан продукт"
    )


class ProductRead(ProductBase):
    id: str
    status: str
    current_zone: str
    warehouse_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductEdit(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    article: Optional[str] = Field(None, min_length=1)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    current_row: Optional[int] = Field(None, ge=0)
    current_shelf: Optional[str] = Field(None, min_length=1, max_length=2)
    warehouse_id: Optional[str] = Field(None, min_length=1)
