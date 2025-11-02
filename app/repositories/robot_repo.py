from typing import Optional, List,Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,distinct,func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import noload, load_only

from app.models.robot import Robot
from app.models.warehouse import Warehouse


class RobotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        id: str,
        status: str,
        battery_level: int,
        current_zone: str,
        current_row: int,
        current_shelf: str,
        warehouse_id: str,
        check_warehouse_exists: bool = True,
    ) -> Robot:
        if check_warehouse_exists:
            exists = await self.session.scalar(
                select(Warehouse.id).where(Warehouse.id == warehouse_id)
            )
            if not exists:
                raise ValueError(f"Склад '{warehouse_id}' не найден")
        
        robot = Robot(
            id=id,
            status=status,
            battery_level=battery_level,
            current_zone=current_zone,
            current_row=current_row,
            current_shelf=current_shelf,
            warehouse_id = warehouse_id
        )

        self.session.add(robot)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
        await self.session.refresh(robot)
        return robot
    
    async def get(self, id: str) -> Optional[Robot]:
        return await self.session.scalar(
            select(Robot).where(Robot.id == id)
        )
    
    async def get_all_by_warehouse_id(self, warehosue_id: str):
        stmt = (
        select(Robot)
        .where(Robot.warehouse_id == warehouse_id)
        .options(
            noload(Robot.warehouse),
            noload(Robot.history),
            noload(Robot.robot_history),
            load_only(Robot.id, Robot.status, Robot.battery_level,
                    Robot.current_zone, Robot.current_row, Robot.current_shelf,
                    Robot.warehouse_id, Robot.created_at)
            )
        )
        res = await self.session.execute(stmt)
        robots = list(res.scalars().all())

    async def delete(self, id: str):
        robot = await self.session.scalar(
            select(Robot).where(Robot.id == id)
        )

        if not robot:
            raise ValueError(f"Робот с id '{id}' не найден.")

        await self.session.delete(robot)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
    
    async def avg_battery_by_warehouse(self, warehouse_id: str) -> float:
        val = await self.session.scalar(
            select(func.avg(Robot.battery_level)).where(Robot.warehouse_id == warehouse_id)
        )
        return float(val or 0.0)

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(Robot.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]:
        return await self.session.scalar(
            select(Robot.warehouse_id).where(Robot.id == robot_id)
        )
    
    async def total_robots(self, warehouse_id: str) -> int:
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == warehouse_id)
        )
        return int(val or 0)

    async def counts_by_status(
        self, warehouse_id: str, only_statuses: Tuple[str, ...]
    ) -> Dict[str, int]:
        stmt = (
            select(
                func.lower(Robot.status).label("status"),
                func.count(Robot.id).label("cnt"),
            )
            .where(Robot.warehouse_id == warehouse_id)
            .where(func.lower(Robot.status).in_(tuple(s.lower() for s in only_statuses)))
            .group_by(func.lower(Robot.status))
        )
        rows = (await self.session.execute(stmt)).all()
        return {str(status): int(cnt) for status, cnt in rows}

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(Robot.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]:
        return await self.session.scalar(
            select(Robot.warehouse_id).where(Robot.id == robot_id)
        )

    # 1) Узкая загрузка для тика эмулятора
    async def load_for_tick(self, robot_id: str) -> Optional[Robot]:
        res = await self.session.execute(
            select(Robot)
            .options(
                load_only(
                    Robot.id, Robot.warehouse_id, Robot.status,
                    Robot.battery_level, Robot.current_row, Robot.current_shelf,
                ),
                noload(Robot.warehouse),
                noload(Robot.history),
                noload(Robot.robot_history),
            )
            .where(Robot.id == robot_id)
        )
        return res.scalar_one_or_none()

    # 2) Обновление координат и/или статуса (под открытой транзакцией)
    async def update_xy_and_status(
        self,
        robot: Robot,
        current_shelf: int | str | None,
        current_row: int | None,
        status: Optional[str],
    ) -> None:
        if current_shelf is not None:
            try:
                robot.current_shelf = int(current_shelf)
            except Exception:
                robot.current_shelf = 0
        if current_row is not None:
            robot.current_row = int(current_row)
        if status is not None:
            robot.status = status

        await self.session.flush()

    # 3) Все id роботов по складу (без лишних join)
    async def list_ids_by_warehouse(self, warehouse_id: str) -> List[str]:
        res = await self.session.execute(
            select(Robot.id).where(Robot.warehouse_id == warehouse_id)
        )
        return list(res.scalars().all())

    # 4) Средняя батарея по складу (для battery_events)
    async def avg_battery_by_warehouse(self, warehouse_id: str) -> float:
        avg = await self.session.scalar(
            select(func.avg(Robot.battery_level)).where(Robot.warehouse_id == warehouse_id)
        )
        return float(avg or 0.0)

    # 5) Список складов, где есть роботы (для стримеров)
    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(
            select(func.distinct(Robot.warehouse_id))
        )
        return [wid for (wid,) in rows.all() if wid]

    # 6) Общее число роботов на складе (для active_robots стримера)
    async def total_robots(self, warehouse_id: str) -> int:
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == warehouse_id)
        )
        return int(val or 0)

    # 7) Количество роботов по активным статусам (для active_robots стримера)
    async def count_active_by_status(
        self,
        warehouse_id: str,
        active_statuses: Tuple[str, ...],
    ) -> Dict[str, int]:
        rows = await self.session.execute(
            select(func.lower(Robot.status), func.count(Robot.id))
            .where(Robot.warehouse_id == warehouse_id)
            .where(func.lower(Robot.status).in_(active_statuses))
            .group_by(func.lower(Robot.status))
        )
        return {str(status): int(cnt) for status, cnt in rows.all()}