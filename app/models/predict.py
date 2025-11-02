from __future__ import annotations
from sqlalchemy import Column, String, DateTime, Integer, Float, func
from app.db.base import Base


class PredictAt(Base):
    """
    Таблица прогнозов истощения запасов (результаты ML-предсказаний).
    Содержит дату предполагаемого исчерпания, доверительные интервалы и вероятность.
    """

    __tablename__ = "predict_at"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Идентификаторы
    product_id = Column(String, nullable=False, index=True)
    product_name = Column(String, nullable=True)
    warehouse_id = Column(String, nullable=False, index=True)

    # Основной прогноз
    depletion_at = Column(DateTime(timezone=True), nullable=True)

    # Доверительные интервалы
    depletion_at_p10 = Column(DateTime(timezone=True), nullable=True)
    depletion_at_p90 = Column(DateTime(timezone=True), nullable=True)

    # Вероятность, что истощение произойдет в горизонте прогноза
    p_deplete_within = Column(Float, nullable=True)

    # Время генерации прогноза
    predicted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"<PredictAt(product_id={self.product_id}, "
            f"warehouse_id={self.warehouse_id}, "
            f"depletion_at={self.depletion_at}, "
            f"p_within={self.p_deplete_within})>"
        )
