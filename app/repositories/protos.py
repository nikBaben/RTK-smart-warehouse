from __future__ import annotations
import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Protocol,
    runtime_checkable,
    Optional,
    Iterable,
    List,
    Tuple,
    Dict,
    Any,
)

from app.models.robot import Robot
from app.models.product import Product


@runtime_checkable
class RobotRepositoryProto(Protocol):
    async def load_for_tick(self, robot_id: str) -> Optional[Robot]:

    async def update_xy_and_status(
        self,
        robot: Robot,
        current_shelf: int | str | None,
        current_row: int | None,
        status: str | None,
    ) -> None:

    async def list_ids_by_warehouse(self, warehouse_id: str) -> List[str]:


@runtime_checkable
class RobotHistoryRepositoryProto(Protocol):
    async def log(self, robot_id: str, warehouse_id: str, status: str, created_at: datetime) -> None:


@runtime_checkable
class ProductRepositoryProto(Protocol):
    #Давность» сканов (инициализация ZSET)
    async def min_scan_seed_rows(self, warehouse_id: str) -> List[Tuple[int, str, datetime]]:

    #Быстрый фильтр «есть ли eligible-товары в этих клетках
    async def eligible_cells_by_pairs(
        self,
        warehouse_id: str,
        row_shelf_pairs: List[Tuple[int, str]],
        cutoff: datetime,
    ) -> List[Tuple[int, str]]:

    async def eligible_cells_fallback(
        self,
        warehouse_id: str,
        cutoff: datetime,
    ) -> List[Tuple[int, str, datetime]]:

    #Список товаров для скана в конкретной клетке
    async def eligible_products_in_cell(
        self,
        warehouse_id: str,
        shelf_num: int,
        row_num: int,
        cutoff: datetime,
    ) -> List[Product]:

    #Массовая пометка времени скана
    async def mark_last_scanned(self, product_ids: Iterable[str], when: datetime) -> None:


# InventoryHistoryRepository
@runtime_checkable
class InventoryHistoryRepositoryProto(Protocol):
    async def get_last_scans(self, warehouse_id: str, limit: int) -> List[Dict[str, Any]]:

    async def insert_rows(self, rows: List[Dict[str, Any]]) -> None:


# WarehouseRepository
@runtime_checkable
class WarehouseRepositoryProto(Protocol):
    async def ids_having_robots(self) -> List[str]:


@dataclass
class RepoBundle:
    robot: RobotRepositoryProto
    robot_history: RobotHistoryRepositoryProto
    product: ProductRepositoryProto
    inv_hist: InventoryHistoryRepositoryProto
    warehouse: WarehouseRepositoryProto
