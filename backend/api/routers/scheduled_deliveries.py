from fastapi import APIRouter, Depends
from backend.schemas.scheduled_delivery import ScheduledDeliveryIn, ScheduledDeliveryOut
from backend.service.scheduled_delivery_service import ScheduledDeliveryService
from backend.api.deps import get_scheduled_delivery_service

router = APIRouter(prefix="/scheduled_deliveries", tags=["deliveries"])


@router.post("", response_model=ScheduledDeliveryOut, status_code=201)
async def create_scheduled_delivery(
    payload: ScheduledDeliveryIn,
    service: ScheduledDeliveryService = Depends(get_scheduled_delivery_service),
):
    return await service.create(payload)
