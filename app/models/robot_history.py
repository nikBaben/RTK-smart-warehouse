from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class RobotHistory(Base):
    __tablename__ = "robot_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    robot_id: Mapped[str | None] = mapped_column(  
        String(50),
        ForeignKey("robots.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False) 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    robot = relationship("Robot", back_populates="robot_history", lazy="joined")

    __table_args__ = (
        # «последние записи по роботу»
        Index("ix_rh_robot_created", "robot_id", "created_at"),
        # «срез по складу и статусу во времени»
        Index("ix_rh_wh_status_created", "warehouse_id", "status", "created_at"),
        # «общая временная ось по складу»
        Index("ix_rh_wh_created", "warehouse_id", "created_at"),
    )