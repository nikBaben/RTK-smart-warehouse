from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    article: Mapped[Optional[str]] = mapped_column(String(100))
    stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    min_stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    optimal_stock: Mapped[int] = mapped_column(Integer, nullable=False, server_default="80")
    current_zone: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Хранение")
    current_row: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    current_shelf: Mapped[str] = mapped_column(String(2), nullable=False, server_default="A")  # 'A'..'Z'
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ok")

    # ⬇️ НОВОЕ поле для горячего пути «когда последний раз сканировали»
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    warehouse_id: Mapped[str] = mapped_column(
    String(50),
    ForeignKey("warehouses.id", ondelete="CASCADE"),
    nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="products", lazy="joined")  # type: ignore
    history: Mapped[List["InventoryHistory"]] = relationship(
        back_populates="product",
        lazy="selectin",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    __table_args__ = (
        # выборка «товары в ячейке»
        Index("ix_products_wh_row_shelf", "warehouse_id", "current_row", "current_shelf"),
        # частые фильтры по названию в рамках склада
        Index("ix_products_wh_name", "warehouse_id", "name"),
        # ⬇️ НОВЫЙ индекс под eligible-запросы:
        # warehouse + (row,shelf) + last_scanned_at с инклюдами под отдачу данных
        Index(
            "ix_products_wh_cell_lastscan",
            "warehouse_id",
            "current_row",
            "current_shelf",
            "last_scanned_at",
            postgresql_include=("id","name","category","article","stock","min_stock","optimal_stock"),
        ),
    )