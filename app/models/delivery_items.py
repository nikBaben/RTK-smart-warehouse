from __future__ import annotations


from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class DeliveryItems(Base):
    __tablename__ = "delivery_items"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    delivery_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("deliveries.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("products.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("warehouses.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True
    )
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fact_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    delivery: Mapped[Optional["Delivery"]] = relationship("Delivery", lazy="joined")
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="joined")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="joined")