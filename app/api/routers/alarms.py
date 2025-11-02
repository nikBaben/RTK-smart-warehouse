from fastapi import APIRouter, Depends, status
from app.schemas.alarm import AlarmCreate, AlarmResponse
from app.service.robot_service import AlarmService
from app.api.deps import get_alarm_service  
from app.api.deps import keycloak_auth_middleware  

router = APIRouter(prefix="/alarms", tags=["alarms"])#,dependencies=[Depends(keycloak_auth_middleware)]

@router.get(
    "",
    response_model=list[AlarmResponse],
    status_code=status.HTTP_200_OK,
    summary="Уведомления по id",
)
async def get_robots_by_warehouse_id(
    warehouse_id: str,
    service: AlarmService = Depends(get_alarm_service),
):
    robots = await service.get_robots_by_warehouse_id(warehouse_id)
    return robots

"""@router.delete(
        "/{alarm_id}",
        summary="Удалить Уведомление",
)
async def delete_warehouse(
    robot_id: str,
    service: RobotService = Depends(get_robot_service),
):
    return await service.delete_robot(robot_id)"""
