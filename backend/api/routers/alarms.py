from fastapi import APIRouter, Depends
from backend.schemas.alarm import AlarmResponse
from backend.service.alarm_service import AlarmService
from backend.api.deps import get_alarm_service

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.get("", response_model=list[AlarmResponse])
async def get_alarms(user_id: int, service: AlarmService = Depends(get_alarm_service)):
    return await service.get_alarms(user_id)
