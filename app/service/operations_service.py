from typing import List
from app.repositories.operations_repo import OperationsRepository
from app.schemas.supplies import AllOperationsResponse, DeliveryShortResponse, ShipmentShortResponse
from app.models.delivery import Delivery
from app.models.shipment import Shipment


class OperationsService:
    def __init__(self, repo: OperationsRepository):
        self.repo = repo

    async def get_all_operations_by_warehouse(self, warehouse_id: str) -> AllOperationsResponse:
        """Получить все поставки и отгрузки для конкретного склада"""
        deliveries, shipments = await self.repo.get_all_operations_by_warehouse(warehouse_id)
        
        delivery_responses = [
            DeliveryShortResponse(
                id=delivery.id,
                name=delivery.name,
                supplier=delivery.supplier,
                scheduled_at=delivery.scheduled_at,
                quantity=delivery.quantity,
                status=delivery.status,
                warehouse_id=delivery.warehouse_id
            )
            for delivery in deliveries
        ]
        
        shipment_responses = [
            ShipmentShortResponse(
                id=shipment.id,
                name=shipment.name,
                customer=shipment.customer,
                scheduled_at=shipment.scheduled_at,
                quantity=shipment.quantity,
                status=shipment.status,
                warehouse_id=shipment.warehouse_id
            )
            for shipment in shipments
        ]
        
        return AllOperationsResponse(
            deliveries=delivery_responses,
            shipments=shipment_responses
        )

    async def get_all_deliveries_by_warehouse(self, warehouse_id: str) -> List[DeliveryShortResponse]:
        """Получить только поставки для конкретного склада"""
        deliveries = await self.repo.get_all_deliveries_by_warehouse(warehouse_id)
        return [
            DeliveryShortResponse(
                id=delivery.id,
                name=delivery.name,
                supplier=delivery.supplier,
                scheduled_at=delivery.scheduled_at,
                quantity=delivery.quantity,
                status=delivery.status,
                warehouse_id=delivery.warehouse_id
            )
            for delivery in deliveries
        ]

    async def get_all_shipments_by_warehouse(self, warehouse_id: str) -> List[ShipmentShortResponse]:
        """Получить только отгрузки для конкретного склада"""
        shipments = await self.repo.get_all_shipments_by_warehouse(warehouse_id)
        return [
            ShipmentShortResponse(
                id=shipment.id,
                name=shipment.name,
                customer=shipment.customer,
                scheduled_at=shipment.scheduled_at,
                quantity=shipment.quantity,
                status=shipment.status,
                warehouse_id=shipment.warehouse_id
            )
            for shipment in shipments
        ]