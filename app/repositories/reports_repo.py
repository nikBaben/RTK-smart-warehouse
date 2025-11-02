from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract, and_
from typing import List, Tuple
from datetime import datetime
from app.models.delivery import Delivery
from app.models.shipment import Shipment


class ReportsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_deliveries_by_month_and_warehouse(self, year: int, month: int, warehouse_id: str) -> List[Delivery]:
        result = await self.session.execute(
            select(Delivery)
            .where(
                and_(
                    extract('year', Delivery.scheduled_at) == year,
                    extract('month', Delivery.scheduled_at) == month,
                    Delivery.warehouse_id == warehouse_id
                )
            )
            .order_by(Delivery.scheduled_at)
        )
        return result.scalars().all()

    async def get_shipments_by_month_and_warehouse(self, year: int, month: int, warehouse_id: str) -> List[Shipment]:
        result = await self.session.execute(
            select(Shipment)
            .where(
                and_(
                    extract('year', Shipment.scheduled_at) == year,
                    extract('month', Shipment.scheduled_at) == month,
                    Shipment.warehouse_id == warehouse_id
                )
            )
            .order_by(Shipment.scheduled_at)
        )
        return result.scalars().all()

    async def get_operations_by_year_and_warehouse(self, year: int, warehouse_id: str) -> Tuple[List[Delivery], List[Shipment]]:
        deliveries_result = await self.session.execute(
            select(Delivery)
            .where(
                and_(
                    extract('year', Delivery.scheduled_at) == year,
                    Delivery.warehouse_id == warehouse_id
                )
            )
            .order_by(Delivery.scheduled_at)
        )
        
        shipments_result = await self.session.execute(
            select(Shipment)
            .where(
                and_(
                    extract('year', Shipment.scheduled_at) == year,
                    Shipment.warehouse_id == warehouse_id
                )
            )
            .order_by(Shipment.scheduled_at)
        )
        
        return deliveries_result.scalars().all(), shipments_result.scalars().all()