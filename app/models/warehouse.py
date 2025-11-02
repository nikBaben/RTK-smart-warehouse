from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    max_products: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # размеры поля (x: 0..row_x-1, y: 1..min(row_y,26))
    row_x:  Mapped[int] = mapped_column(Integer, nullable=False, server_default="26")
    row_y:  Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    products_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products: Mapped[List["Product"]] = relationship(  # type: ignore
        back_populates="warehouse",
        lazy="selectin",
        cascade="save-update, merge",     
        passive_deletes=True,
    )

    robots: Mapped[List["Robot"]] = relationship(  # type: ignore
        back_populates="warehouse",
        lazy="selectin",
        cascade="save-update, merge",
        passive_deletes=True,
    )
    
    shipments: Mapped[list["Shipment"]] = relationship(
        back_populates="warehouse",
        cascade="all, delete-orphan"
    )

    inventory_history: Mapped[List["InventoryHistory"]] = relationship(  # type: ignore
        back_populates="warehouse",
        lazy="selectin",
        cascade="save-update, merge",      
        passive_deletes=True,
    )