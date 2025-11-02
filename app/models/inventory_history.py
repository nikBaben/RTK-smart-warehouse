from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class InventoryHistory(Base):
    __tablename__ = "inventory_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    product_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("products.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    robot_id: Mapped[Optional[str]] = mapped_column(
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

    robot = relationship("Robot", back_populates="history", lazy="joined")
    product = relationship("Product", back_populates="history", lazy="joined")
    warehouse = relationship("Warehouse", back_populates="inventory_history", lazy="joined")

    current_zone: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Хранение")
    current_row: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    current_shelf: Mapped[str] = mapped_column(String(2), nullable=False, server_default="A")

    name: Mapped[Optional[str]] = mapped_column(String(255))
    category: Mapped[Optional[str]] = mapped_column(String(100))
    article: Mapped[Optional[str]] = mapped_column(String(100))
    stock: Mapped[Optional[int]] = mapped_column(Integer)
    min_stock: Mapped[Optional[int]] = mapped_column(Integer)
    optimal_stock: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        # «последний скан по товару в рамках склада»
        Index("ix_inv_hist_wh_prod_created", "warehouse_id", "product_id", "created_at"),
        # поиск по роботу во времени
        Index("ix_inv_hist_robot_created", "robot_id", "created_at"),
        # общий временной индекс по складу
        Index("ix_inv_hist_wh_created", "warehouse_id", "created_at"),
    )