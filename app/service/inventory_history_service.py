import time
import random
import string

from uuid import uuid4
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
from datetime import datetime

from app.repositories.inventory_history_repo import InventoryHistoryRepository
from app.models.inventory_history import InventoryHistory

class InventoryHistoryService:
    def __init__(self, repo: InventoryHistoryRepository):
        self.repo = repo

    async def create_id(self) -> str:
        alphabet = string.digits + string.ascii_uppercase  # 0-9 + A-Z

        def base36(num):
            return ''.join(
                alphabet[num // 36 ** i % 36] for i in reversed(range(2))
            )

        ts = int(time.time()) % 100000
        rnd = random.randint(0, 1295)
        return base36(ts % 1296) + base36(rnd)

        
    async def get_inventory_history_by_warehouse_id(self, warehouse_id: str):
        inventory_history = await self.repo.get_all_by_warehouse_id(warehouse_id)
        if not inventory_history:
            raise ValueError(f"История инвентаризации на скалде id '{warehouse_id}' не найдена.")
        return inventory_history
    
    async def get_filtered_inventory_history(
        self, 
        warehouse_id: str,
        filters: Dict[str, Any],
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int
    ) -> Tuple[List[Tuple[InventoryHistory, Any, int]], int]:

        inventory_history = await self.repo.get_filtered_inventory_history(
            warehouse_id=warehouse_id,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"с примененными фильтрами не найдена."
            )
        return inventory_history
    

    async def inventory_history_export_to_xl(
        self, 
        warehouse_id: str,
        record_ids: List[str]
    ) -> BytesIO:

        inventory_history = await self.repo.inventory_history_export_to_xl(
            warehouse_id=warehouse_id,
             record_ids= record_ids
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"не найдена."
            )
        return inventory_history
    

    async def inventory_history_export_to_pdf(
        self, 
        warehouse_id: str,
        record_ids: List[str]
    ) -> BytesIO:

        inventory_history = await self.repo.inventory_history_export_to_pdf(
            warehouse_id=warehouse_id,
             record_ids= record_ids
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"не найдена."
            )
        return inventory_history
    
    async def inventory_history_create_graph(
        self, 
        warehouse_id: str,
        record_ids: List[str]
        ) -> Dict[str, List[Tuple[datetime, int]]]:

        inventory_history = await self.repo.inventory_history_create_graph(
            warehouse_id=warehouse_id,
             record_ids= record_ids
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"не найдена."
            )
        return inventory_history
    
    async def inventory_history_unique_categories(
        self, 
        warehouse_id: str
        ) -> List[str]:

        inventory_history = await self.repo.inventory_history_unique_categories(
            warehouse_id=warehouse_id,
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"не найдена."
            )
        return inventory_history
    
    async def inventory_history_unique_zones(
        self, 
        warehouse_id: str
        ) -> List[str]:

        inventory_history = await self.repo.inventory_history_unique_zones(
            warehouse_id=warehouse_id,
        )
        
        if not inventory_history:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' "
                f"не найдена."
            )
        return inventory_history
    

    async def import_inventory_from_csv(
        self,
        warehouse_id: str,
        csv_data: str,
    ) -> None:
        
        await self.repo.import_inventory_from_csv(
            warehouse_id=warehouse_id, csv_data = csv_data
        )

    async def get_statistic(
        self,
        warehouse_id: str,
    ) -> Dict:
        
        stat = await self.repo.get_statistic(
            warehouse_id=warehouse_id
        )

        return stat