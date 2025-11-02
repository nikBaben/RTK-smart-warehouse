from typing import Optional, List, Dict, Tuple, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import noload, load_only

from app.models.robot import Robot
from app.models.warehouse import Warehouse


class RobotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ──────────────────────────────────────────────────────────────
    # Создание нового робота
    # ──────────────────────────────────────────────────────────────
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
        wid = str(warehouse_id)

        if check_warehouse_exists:
            exists = await self.session.scalar(
                select(Warehouse.id).where(Warehouse.id == wid)
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
            warehouse_id=wid,
        )

        self.session.add(robot)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
        await self.session.refresh(robot)
        return robot

    # Получение робота по ID
    async def get(self, id: str) -> Optional[Robot]:
        return await self.session.scalar(select(Robot).where(Robot.id == id))

    # Список роботов по складу
    async def get_all_by_warehouse_id(self, warehouse_id: str) -> Sequence[Robot]:
        wid = str(warehouse_id)
        stmt = (
            select(Robot)
            .where(Robot.warehouse_id == wid)
            .options(
                noload(Robot.warehouse),
                noload(Robot.history),
                load_only(
                    Robot.id,
                    Robot.status,
                    Robot.battery_level,
                    Robot.current_zone,
                    Robot.current_row,
                    Robot.current_shelf,
                    Robot.warehouse_id,
                    Robot.created_at,
                ),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    # ──────────────────────────────────────────────────────────────
    # Удаление робота
    # ──────────────────────────────────────────────────────────────
    async def delete(self, id: str) -> None:
        robot = await self.session.scalar(select(Robot).where(Robot.id == id))
        if not robot:
            raise ValueError(f"Робот с id '{id}' не найден.")

        await self.session.delete(robot)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise e

    # ──────────────────────────────────────────────────────────────
    # Средний уровень батареи по складу
    # ──────────────────────────────────────────────────────────────
    async def avg_battery_by_warehouse(self, warehouse_id: str) -> float:
        wid = str(warehouse_id)
        val = await self.session.scalar(
            select(func.avg(Robot.battery_level)).where(Robot.warehouse_id == wid)
        )
        return float(val or 0.0)

    # ──────────────────────────────────────────────────────────────
    # Все уникальные склады, где есть роботы
    # ──────────────────────────────────────────────────────────────
    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(Robot.warehouse_id)))
        return [str(wid) for (wid,) in rows.all() if wid]

    # ──────────────────────────────────────────────────────────────
    # Получить склад по ID робота
    # ──────────────────────────────────────────────────────────────
    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]:
        val = await self.session.scalar(
            select(Robot.warehouse_id).where(Robot.id == robot_id)
        )
        return str(val) if val else None

    # ──────────────────────────────────────────────────────────────
    # Узкая загрузка для тика эмулятора
    # ──────────────────────────────────────────────────────────────
    async def load_for_tick(self, robot_id: str) -> Optional[Robot]:
        res = await self.session.execute(
            select(Robot)
            .options(
                load_only(
                    Robot.id,
                    Robot.warehouse_id,
                    Robot.status,
                    Robot.battery_level,
                    Robot.current_row,
                    Robot.current_shelf,
                ),
                noload(Robot.warehouse),
                noload(Robot.history),
            )
            .where(Robot.id == robot_id)
        )
        return res.scalar_one_or_none()

    # ──────────────────────────────────────────────────────────────
    # Обновление координат и/или статуса (под открытой транзакцией)
    # ──────────────────────────────────────────────────────────────
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

    # ──────────────────────────────────────────────────────────────
    # Все ID роботов по складу (без лишних join)
    # ──────────────────────────────────────────────────────────────
    async def list_ids_by_warehouse(self, warehouse_id: str) -> List[str]:
        wid = str(warehouse_id)
        res = await self.session.execute(
            select(Robot.id).where(Robot.warehouse_id == wid)
        )
        return list(res.scalars().all())

    # ──────────────────────────────────────────────────────────────
    # Общее число роботов на складе
    # ──────────────────────────────────────────────────────────────
    async def total_robots(self, warehouse_id: str) -> int:
        wid = str(warehouse_id)
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == wid)
        )
        return int(val or 0)

    # ──────────────────────────────────────────────────────────────
    # Количество роботов по активным статусам
    # ──────────────────────────────────────────────────────────────
    async def count_active_by_status(
        self,
        warehouse_id: str,
        active_statuses: Tuple[str, ...],
    ) -> Dict[str, int]:
        wid = str(warehouse_id)
        rows = await self.session.execute(
            select(func.lower(Robot.status), func.count(Robot.id))
            .where(Robot.warehouse_id == wid)
            .where(func.lower(Robot.status).in_(tuple(s.lower() for s in active_statuses)))
            .group_by(func.lower(Robot.status))
        )
        return {str(status): int(cnt) for status, cnt in rows.all()}

    # ──────────────────────────────────────────────────────────────
    # Количество роботов по статусам (общая версия)
    # ──────────────────────────────────────────────────────────────
    async def counts_by_status(
        self, warehouse_id: str, only_statuses: Tuple[str, ...]
    ) -> Dict[str, int]:
        wid = str(warehouse_id)
        rows = await self.session.execute(
            select(func.lower(Robot.status), func.count(Robot.id))
            .where(Robot.warehouse_id == wid)
            .where(func.lower(Robot.status).in_(tuple(s.lower() for s in only_statuses)))
            .group_by(func.lower(Robot.status))
        )
        return {str(status): int(cnt) for status, cnt in rows.all()}
