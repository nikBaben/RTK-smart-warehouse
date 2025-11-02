from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.service.shipment_service import ShipmentService
from app.schemas.supplies import ShipmentDetailResponse, ShipmentItemDetailResponse
from app.api.deps import get_shipment_service

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("/{shipment_id}", response_model=ShipmentDetailResponse)
async def get_shipment(
    shipment_id: str,
    shipment_service: ShipmentService = Depends(get_shipment_service)
):
    """Получить отгрузку по ID"""
    shipment = await shipment_service.get_shipment_by_id(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.get("/{shipment_id}/items", response_model=List[ShipmentItemDetailResponse])
async def get_shipment_items(
    shipment_id: str,
    shipment_service: ShipmentService = Depends(get_shipment_service)
):
    """Получить элементы отгрузки"""
    return await shipment_service.get_shipment_items(shipment_id)


@router.get("/items/{item_id}", response_model=ShipmentItemDetailResponse)
async def get_shipment_item(
    item_id: str,
    shipment_service: ShipmentService = Depends(get_shipment_service)
):
    """Получить элемент отгрузки по ID"""
    item = await shipment_service.get_shipment_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shipment item not found")
    return item

@router.delete("/{shipment_id}")
async def delete_shipment(
    shipment_id: str,
    shipment_service: ShipmentService = Depends(get_shipment_service)
):
    """Удалить отгрузку и все ее элементы"""
    success = await shipment_service.delete_shipment(shipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return {"message": "Shipment deleted successfully"}


@router.delete("/items/{item_id}")
async def delete_shipment_item(
    item_id: str,
    shipment_service: ShipmentService = Depends(get_shipment_service)
):
    """Удалить элемент отгрузки по ID"""
    success = await shipment_service.delete_shipment_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Shipment item not found")
    return {"message": "Shipment item deleted successfully"}