from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.models.robot import Robot
from backend.models.robot_history import RobotHistory


class RobotHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self, robot_id: str, warehouse_id: str, status: str, created_at: datetime
    ) -> None:
        self.session.add(
            RobotHistory(
                id=str(uuid4()),
                robot_id=robot_id,
                warehouse_id=warehouse_id,
                status=status,
                created_at=created_at,
            )
        )
        await self.session.flush()

    async def total_robots(self, warehouse_id: str) -> int:
        val = await self.session.scalar(
            select(func.count(Robot.id)).where(Robot.warehouse_id == warehouse_id)
        )
        return int(val or 0)

    async def latest_history_timestamp(self, warehouse_id: str) -> Optional[datetime]:
        ts = await self.session.scalar(
            select(func.max(RobotHistory.created_at)).where(
                RobotHistory.warehouse_id == warehouse_id
            )
        )
        return ts

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
            .where(
                and_(
                    RobotHistory.warehouse_id == warehouse_id,
                    RobotHistory.created_at < before_ts,
                )
            )
            .group_by(RobotHistory.robot_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(RobotHistory.robot_id, RobotHistory.status).join(
                sub,
                and_(
                    RobotHistory.robot_id == sub.c.rid,
                    RobotHistory.created_at == sub.c.mx,
                ),
            )
        )
        out: Dict[str, str] = {}
        for rid, status in rows.all():
            out[str(rid)] = (status or "").lower()
        return out

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

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(
            select(func.distinct(RobotHistory.warehouse_id))
        )
        return [wid for (wid,) in rows.all() if wid]

    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]:
        wid = await self.session.scalar(
            select(RobotHistory.warehouse_id).where(RobotHistory.id == history_id)
        )
        return wid
