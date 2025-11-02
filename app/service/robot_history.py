from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.robot import Robot
from app.models.robot_history import RobotHistory
import uuid

async def write_robot_status_event(session: AsyncSession, robot_id: str) -> None:
    # берём текущие поля
    row = await session.execute(select(Robot.status, Robot.warehouse_id).where(Robot.id == robot_id))
    cur = row.one_or_none()
    if not cur:
        return
    status, warehouse_id = cur
    event = RobotHistory(
        id=str(uuid.uuid4()),
        robot_id=robot_id,
        warehouse_id=warehouse_id,
        status=status,
    )
    session.add(event)
    # коммит производится в вызывающем коде (или здесь, если так принято)
