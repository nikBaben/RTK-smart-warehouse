# app/repositories/protos.py
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

# Типы из моделей используются только для аннотаций — импорт безопасен.
# Если где-то появится циклическая зависимость, можно заменить на 'Any'.
from app.models.robot import Robot
from app.models.product import Product


# ===============================
# RobotRepository
# ===============================
@runtime_checkable
class RobotRepositoryProto(Protocol):
    async def load_for_tick(self, robot_id: str) -> Optional[Robot]:
        """
        Узкий «горячий» лоад робота для тика симуляции:
        должен подгрузить только нужные поля (id, warehouse_id, status, battery_level, current_row, current_shelf).
        """

    async def update_xy_and_status(
        self,
        robot: Robot,
        current_shelf: int | str | None,
        current_row: int | None,
        status: str | None,
    ) -> None:
        """
        Обновление координат и статуса робота (без лишних JOIN’ов/relationship’ов).
        Реализация должна вызвать flush/commit в рамках внешней транзакции (или только flush).
        """

    async def list_ids_by_warehouse(self, warehouse_id: str) -> List[str]:
        """
        Вернёт все robot.id по складу (без джойнов).
        """


# ===============================
# RobotHistoryRepository
# ===============================
@runtime_checkable
class RobotHistoryRepositoryProto(Protocol):
    async def log(self, robot_id: str, warehouse_id: str, status: str, created_at: datetime) -> None:
        """
        Записать событие в RobotHistory (минимальный набор полей).
        """


# ===============================
# ProductRepository
# ===============================
@runtime_checkable
class ProductRepositoryProto(Protocol):
    # ---- «Давность» сканов (инициализация ZSET) ----
    async def min_scan_seed_rows(self, warehouse_id: str) -> List[Tuple[int, str, datetime]]:
        """
        Вернуть агрегат по складу:
        List[(row:int, shelf_str:str, min_scan_at:datetime)] — где min_scan_at = MIN(COALESCE(last_scanned_at, EPOCH))
        для каждой (row, shelf_str != '0').
        """

    # ---- Быстрый фильтр «есть ли eligible-товары в этих клетках» ----
    async def eligible_cells_by_pairs(
        self,
        warehouse_id: str,
        row_shelf_pairs: List[Tuple[int, str]],
        cutoff: datetime,
    ) -> List[Tuple[int, str]]:
        """
        По списку (row, shelf_str) вернуть только те пары, где есть товары:
          last_scanned_at IS NULL OR last_scanned_at < cutoff.
        Возвращает те же пары (row, shelf_str).
        """

    # ---- Fallback выборка самых «старых» клеток одной SQL ----
    async def eligible_cells_fallback(
        self,
        warehouse_id: str,
        cutoff: datetime,
    ) -> List[Tuple[int, str, datetime]]:
        """
        Вернуть List[(row:int, shelf_str:str, min_scan:datetime)] в порядке возрастания min(last_scanned_at|EPOCH)
        по клеткам (row, shelf_str != '0'), где есть eligible-товары.
        """

    # ---- Список товаров для скана в конкретной клетке ----
    async def eligible_products_in_cell(
        self,
        warehouse_id: str,
        shelf_num: int,
        row_num: int,
        cutoff: datetime,
    ) -> List[Product]:
        """
        Вернуть товары (минимальный набор колонок!), у которых last_scanned_at IS NULL OR < cutoff
        в ячейке (row_num, shelf_num).
        """

    # ---- Массовая пометка времени скана ----
    async def mark_last_scanned(self, product_ids: Iterable[str], when: datetime) -> None:
        """
        Обновить last_scanned_at = when для списка товаров.
        """


# ===============================
# InventoryHistoryRepository
# ===============================
@runtime_checkable
class InventoryHistoryRepositoryProto(Protocol):
    async def get_last_scans(self, warehouse_id: str, limit: int) -> List[Dict[str, Any]]:
        """
        Вернуть последние записи инвентарной истории по складу (limit штук, newest-first).
        Достаточно словарей с полями:
          id, product_id, robot_id, warehouse_id, current_zone, current_row, current_shelf,
          name, category, article, stock, min_stock, optimal_stock, status, created_at
        (created_at — datetime).
        """

    async def insert_rows(self, rows: List[Dict[str, Any]]) -> None:
        """
        Массовая вставка строк в InventoryHistory (bulk insert).
        """


# ===============================
# WarehouseRepository
# ===============================
@runtime_checkable
class WarehouseRepositoryProto(Protocol):
    async def ids_having_robots(self) -> List[str]:
        """
        Вернуть id всех складов, на которых есть хотя бы один робот (DISTINCT).
        """


# ===============================
# Repo bundle
# ===============================
@dataclass
class RepoBundle:
    """
    Удобный контейнер, который предоставляет все репозитории разом.
    Реализация провайдера должна гарантировать единый AsyncSession/транзакцию,
    если это требуется для согласованного обновления.
    """
    robot: RobotRepositoryProto
    robot_history: RobotHistoryRepositoryProto
    product: ProductRepositoryProto
    inv_hist: InventoryHistoryRepositoryProto
    warehouse: WarehouseRepositoryProto
