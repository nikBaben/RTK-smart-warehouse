from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct

from app.models.robot import Robot
from app.models.robot_history import RobotHistory


class RobotHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def total_robots(self, warehouse_id: str) -> int:
        """
        Количество роботов на складе.
        """
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == warehouse_id)
        )
        return int(val or 0)

    async def latest_history_timestamp(self, warehouse_id: str) -> Optional[datetime]:
        """
        Максимальная дата в истории для склада (None, если записей нет).
        """
        return await self.session.scalar(
            select(func.max(RobotHistory.created_at)).where(
                RobotHistory.warehouse_id == warehouse_id
            )
        )

    async def baseline_statuses_before(
        self, warehouse_id: str, before_ts: datetime
    ) -> Dict[str, str]:
        """
        Последний статус каждого робота ДО начала окна (strictly < before_ts).
        Возвращает {robot_id: status_lower}.
        """
        subq = (
            select(
                RobotHistory.robot_id.label("rid"),
                func.max(RobotHistory.created_at).label("mx"),
            )
            .where(
                and_(
                    RobotHistory.warehouse_id == warehouse_id,
                    RobotHistory.created_at < before_ts,
                )
            )
            .group_by(RobotHistory.robot_id)
            .subquery()
        )

        q = (
            select(RobotHistory.robot_id, RobotHistory.status)
            .join(
                subq,
                and_(
                    RobotHistory.robot_id == subq.c.rid,
                    RobotHistory.created_at == subq.c.mx,
                ),
            )
        )

        rows = await self.session.execute(q)
        return {str(rid): (status or "").lower() for rid, status in rows.all()}

    async def events_in_window(
        self,
        warehouse_id: str,
        start_inclusive: datetime,
        end_inclusive: datetime,
    ) -> List[Tuple[str, str, datetime]]:
        """
        События статусов внутри окна [start, end], по времени возрастания.
        Возвращает список кортежей (robot_id, status_lower, created_at).
        """
        q = (
            select(RobotHistory.robot_id, RobotHistory.status, RobotHistory.created_at)
            .where(RobotHistory.warehouse_id == warehouse_id)
            .where(RobotHistory.created_at >= start_inclusive)
            .where(RobotHistory.created_at <= end_inclusive)
            .order_by(RobotHistory.created_at.asc())
        )
        rows = await self.session.execute(q)
        return [(str(rid), (status or "").lower(), ts) for rid, status, ts in rows.all()]

    async def get_distinct_warehouse_ids(self) -> List[str]:
        """
        Список складов, для которых есть события в истории роботов.
        """
        rows = await self.session.execute(select(distinct(RobotHistory.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]:
        """
        Найти склад по идентификатору записи истории.
        """
        return await self.session.scalar(
            select(RobotHistory.warehouse_id).where(RobotHistory.id == history_id)
        )


    async def count_scans_since(self, warehouse_id: str, since_utc: datetime) -> int:
        stmt = (
            select(func.count(InventoryHistory.id))
            .where(InventoryHistory.warehouse_id == warehouse_id)
            .where(InventoryHistory.created_at >= since_utc)
            .where(InventoryHistory.product_id.is_not(None))
        )
        val = await self.session.scalar(stmt)
        return int(val or 0)

    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]:
        return await self.session.scalar(
            select(InventoryHistory.warehouse_id).where(InventoryHistory.id == history_id)
        )

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(InventoryHistory.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    # imports
    from typing import Dict, List, Optional, Tuple
    from datetime import datetime
    from sqlalchemy import select, func, and_
    from app.models.robot_history import RobotHistory
    from app.models.robot import Robot

    # 1) Записать событие истории
    async def log(self, robot_id: str, warehouse_id: str, status: str, created_at: datetime) -> None:
        self.session.add(RobotHistory(
            id = str(uuid4()), 
            robot_id=robot_id,
            warehouse_id=warehouse_id,
            status=status,
            created_at=created_at,
        ))
        await self.session.flush()

    # 2) Всего роботов по складу (нужно для процентов активности)
    async def total_robots(self, warehouse_id: str) -> int:
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == warehouse_id)
        )
        return int(val or 0)

    # 3) Последняя метка времени в истории склада
    async def latest_history_timestamp(self, warehouse_id: str) -> Optional[datetime]:
        ts = await self.session.scalar(
            select(func.max(RobotHistory.created_at)).where(RobotHistory.warehouse_id == warehouse_id)
        )
        return ts

    # 4) Базовые статусы роботов ДО начала окна
    async def baseline_statuses_before(
        self,
        warehouse_id: str,
        before_ts: datetime,
    ) -> Dict[str, str]:
        sub = (
            select(
                RobotHistory.robot_id.label("rid"),
                func.max(RobotHistory.created_at).label("mx"),
            )
            .where(and_(RobotHistory.warehouse_id == warehouse_id,
                        RobotHistory.created_at < before_ts))
            .group_by(RobotHistory.robot_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(RobotHistory.robot_id, RobotHistory.status)
            .join(sub, and_(
                RobotHistory.robot_id == sub.c.rid,
                RobotHistory.created_at == sub.c.mx
            ))
        )
        out: Dict[str, str] = {}
        for rid, status in rows.all():
            out[str(rid)] = (status or "").lower()
        return out

    # 5) События в окне [start, end]
    async def events_in_window(
        self,
        warehouse_id: str,
        start_inclusive: datetime,
        end_inclusive: datetime,
    ) -> List[Tuple[str, str, datetime]]:
        rows = await self.session.execute(
            select(RobotHistory.robot_id, RobotHistory.status, RobotHistory.created_at)
            .where(RobotHistory.warehouse_id == warehouse_id)
            .where(RobotHistory.created_at >= start_inclusive)
            .where(RobotHistory.created_at <= end_inclusive)
            .order_by(RobotHistory.created_at.asc())
        )
        out: List[Tuple[str, str, datetime]] = []
        for rid, status, ts in rows.all():
            out.append((str(rid), (status or "").lower(), ts))
        return out

    # 6) Список складов, где есть история
    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(
            select(func.distinct(RobotHistory.warehouse_id))
        )
        return [wid for (wid,) in rows.all() if wid]

    # 7) Найти склад по id записи истории
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]:
        wid = await self.session.scalar(
            select(RobotHistory.warehouse_id).where(RobotHistory.id == history_id)
        )
        return wid
