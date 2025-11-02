from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.service.delivery_service import DeliveryService
from app.schemas.supplies import DeliveryDetailResponse, DeliveryItemDetailResponse
from app.api.deps import get_delivery_service

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("/{delivery_id}", response_model=DeliveryDetailResponse)
async def get_delivery(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить доставку по ID"""
    delivery = await delivery_service.get_delivery_by_id(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery


@router.get("/{delivery_id}/items", response_model=List[DeliveryItemDetailResponse])
async def get_delivery_items(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить элементы доставки"""
    return await delivery_service.get_delivery_items(delivery_id)


@router.get("/items/{item_id}", response_model=DeliveryItemDetailResponse)
async def get_delivery_item(
    item_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить элемент доставки по ID"""
    item = await delivery_service.get_delivery_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Delivery item not found")
    return item

@router.delete("/{delivery_id}")
async def delete_delivery(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Удалить доставку и все ее элементы"""
    success = await delivery_service.delete_delivery(delivery_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {"message": "Delivery deleted successfully"}


@router.delete("/items/{item_id}")
async def delete_delivery_item(
    item_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Удалить элемент доставки по ID"""
    success = await delivery_service.delete_delivery_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delivery item not found")
    return {"message": "Delivery item deleted successfully"}