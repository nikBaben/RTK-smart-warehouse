from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.service.delivery_service import DeliveryService
from app.schemas.supplies import DeliveryDetailResponse, DeliveryItemDetailResponse
from app.api.deps import get_delivery_service

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

#Получить доставку по ID
@router.get(
    "/{delivery_id}",
    response_model=DeliveryDetailResponse,
    summary="Получить доставку по ID"
)
async def get_delivery(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    delivery = await delivery_service.get_delivery_by_id(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery

#Получить элементы доставки
@router.get(
    "/{delivery_id}/items",
    response_model=List[DeliveryItemDetailResponse],
    summary="Получить элементы доставки"
)
async def get_delivery_items(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    return await delivery_service.get_delivery_items(delivery_id)

#Получить элемент доставки по ID
@router.get(
    "/items/{item_id}",
    response_model=DeliveryItemDetailResponse,
    summary="Получить элемент доставки по ID"
)
async def get_delivery_item(
    item_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    item = await delivery_service.get_delivery_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Delivery item not found")
    return item

#Удалить доставку и все ее элементы
@router.delete("/{delivery_id}")
async def delete_delivery(
    delivery_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service),
    summary="Удалить доставку и все ее элементы"
):
    success = await delivery_service.delete_delivery(delivery_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {"message": "Delivery deleted successfully"}

#Удалить элемент доставки по ID
@router.delete(
    "/items/{item_id}",
    summary="Удалить элемент доставки по ID"
)
async def delete_delivery_item(
    item_id: str,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    success = await delivery_service.delete_delivery_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Delivery item not found")
    return {"message": "Delivery item deleted successfully"}