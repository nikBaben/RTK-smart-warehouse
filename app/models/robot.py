from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="idle")
    battery_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    current_zone: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Хранение")
    current_row: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    current_shelf: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    warehouse_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="robots", lazy="joined")
    history: Mapped[List["InventoryHistory"]] = relationship(
        back_populates="robot",
        lazy="selectin",
        cascade="save-update, merge",    
        passive_deletes=True,
    )
    robot_history: Mapped[List["RobotHistory"]] = relationship(
        back_populates="robot",
        lazy="selectin",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    __table_args__ = (
        # для выборок «активные/по времени»
        Index("ix_robots_wh_status", "warehouse_id", "status"),
    )