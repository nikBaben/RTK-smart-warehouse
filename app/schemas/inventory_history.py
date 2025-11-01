from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field,conint
from typing import Optional, List, Dict, Any, Tuple


class InventoryHistoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Название товара")
    category: str = Field(..., min_length=1, max_length=100, description="Категория товара")
    article:  str = Field(..., min_length=1, max_length=100, description="Артикул товара")
    stock: conint(ge=0) = Field(100, description="Всего товаров") # type: ignore
    #min_stock: conint(ge=0) = Field(20, description="Минимальный запас товара на складе") # type: ignore
    #optimal_stock: conint(ge=0) = Field(80, description="Оптимальный запас товара на складе") # type: ignore
    current_row: int = 0
    current_shelf: str = "A"
    current_zone: str = "Хранение"
    status: str 

    class Config:
        from_attributes = True  


class InventoryHistoryRead(InventoryHistoryBase):
    id: str
    robot_id: Optional[str]
    warehouse_id: Optional[str]
    last_update: Optional[datetime] = None
    created_at: datetime

class InventoryHistoryFilters(BaseModel):
    
    # Фильтры по расположению
    zone_filter: Optional[List[str]] = Field(None, description="Фильтр по зоне")
    
    # Фильтры по товару
    category_filter: Optional[List[str]] = Field(None, description="Фильтр по категории")
    status_filter: Optional[List[str]] = Field(None, description="Фильтр по статусу")
    
    # Фильтры по дате
    date_from: Optional[date] = Field(None, description="Дата с")
    date_to: Optional[date] = Field(None, description="Дата по")

    search_string: Optional[str] = Field(None, description="Фильтр по поисковой строке")

    period_buttons: Optional[List[str]] = Field(
        None, 
        description="Фильтр по периодам: today, yesterday, week, month"
    )

    sort_by: Optional[str] = Field(
        "created_at", 
        description="Поле для сортировки (name, article, created_at, category, status, current_zone, stock)"
    )
    sort_order: Optional[Literal["asc", "desc"]] = Field(
        "desc", 
        description="Направление сортировки: asc или desc"
    )
    page: Optional[int] = Field(
        1, 
        ge=1, 
        description="Номер страницы (начиная с 1)"
    )
    page_size: Optional[int] = Field(
        20, 
        ge=1, 
        le=1000, 
        description="Размер страницы (от 1 до 1000)"
    )

class InventoryHistoryExport(BaseModel):

    record_ids: Optional[List[str]] = Field(
        None, 
        description="Фильтр по периодам: today, yesterday, week, month"
    )


class FilteredInventoryHistoryResponse(BaseModel):
    data: Tuple[List[Tuple[InventoryHistoryRead, Any, int]], int]  

class ChartResponse(BaseModel):
    data: Dict[str, List[Tuple[datetime, int]]]


