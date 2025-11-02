from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ShipmentStatus



class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
    )

    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse", back_populates="shipments"
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ShipmentStatus] = mapped_column(
        SAEnum(ShipmentStatus, name="shipment_status", native_enum=False),
        nullable=False,
        default=ShipmentStatus.scheduled,
    )
    customer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)




class ShipmentItems(Base):
    __tablename__ = "shipment_items"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    shipment_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("shipments.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("products.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("warehouses.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fact_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    shipment: Mapped[Optional["Shipment"]] = relationship("Shipment", lazy="joined")
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="joined")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="joined")