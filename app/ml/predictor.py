# app/ml/predictor.py
from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

import pandas as pd
from prophet import Prophet

from app.ml.model_store import load_model
from app.ml.train import train_for_product  # для автотренировки, если совсем ничего нет
from app.ml.data_access import fetch_snapshot_at, fetch_planned_incoming

log = logging.getLogger("ml.predictor")


def predict_depletion_with_model(
    initial_stock: float,
    planned_incoming_df: pd.DataFrame,
    predicted_outgoing_df: pd.DataFrame,
    freq: str = "D",
) -> Optional[datetime]:
    """
    Детерминированный расчёт даты истощения:
    stock_t+1 = stock_t + incoming_t - outgoing_t
    Возвращает первую дату, когда остаток <= 0, либо None.
    """
    if initial_stock is None or initial_stock <= 0:
        return None

    # Индексы дат
    incoming = (
        planned_incoming_df.set_index(pd.to_datetime(planned_incoming_df["ds"]))["incoming"]
        if not planned_incoming_df.empty else pd.Series(dtype=float)
    )
    outgoing = (
        predicted_outgoing_df.set_index(pd.to_datetime(predicted_outgoing_df["ds"]))["yhat"]
        if not predicted_outgoing_df.empty else pd.Series(dtype=float)
    )

    # Если обе серии пустые — прогнозировать нечего
    if incoming.empty and outgoing.empty:
        return None

    # Избегаем предупреждения pandas о пустых concat
    pieces = []
    if not incoming.empty:
        pieces.append(incoming)
    if not outgoing.empty:
        pieces.append(outgoing)
    if not pieces:
        return None

    all_dates = pd.concat(pieces).index.unique().sort_values()
    incoming = incoming.reindex(all_dates, fill_value=0)
    outgoing = outgoing.reindex(all_dates, fill_value=0).clip(lower=0)

    stock = float(initial_stock)
    for date in all_dates:
        stock += float(incoming.get(date, 0))
        stock -= float(outgoing.get(date, 0))
        if stock <= 0:
            return date.to_pydatetime()
    return None


class Predictor:
    """
    Предиктор на Prophet с fallback-моделью:
      - Пытается загрузить персональную модель /app/models_store/{product_id}.pkl
      - Если её нет, использует базовую default_model_path (например, PROD_DEMO.pkl)
      - Если и её нет — обучает персональную модель "на лету"
    """
    def __init__(
        self,
        model: Optional[Prophet] = None,
        model_path: Optional[str] = None,
        default_model_path: Optional[str] = None,
    ):
        # default_model_path можно задать через ENV, иначе дефолт
        if default_model_path is None:
            default_model_path = os.getenv("DEFAULT_MODEL_PATH", "/app/models_store/PROD_DEMO.pkl")

        self.model: Optional[Prophet] = model
        self.model_path = model_path
        self.default_model_path = default_model_path
        self.prediction: Optional[pd.DataFrame] = None

        if model_path:
            self._load_with_fallback(model_path, default_model_path)

    def _load_with_fallback(self, model_path: str, default_model_path: Optional[str]):
        """
        1) Пытаемся загрузить персональную модель;
        2) если её нет — пробуем базовую DEFAULT;
        3) если и её нет — тренируем персональную (один раз).
        """
        if os.path.exists(model_path):
            self.model = load_model(model_path)
            self.model_path = model_path
            log.info(f"Loaded model: {model_path}")
            return

        if default_model_path and os.path.exists(default_model_path):
            self.model = load_model(default_model_path)
            self.model_path = default_model_path
            log.warning(f"Using fallback model: {default_model_path}")
            return

        # нет и персональной, и базовой — тренируем на лету
        log.warning(f"Model {model_path} not found and no fallback model. Training on the fly...")
        product_id = os.path.basename(model_path).replace(".pkl", "")
        import asyncio
        asyncio.run(train_for_product(product_id, model_path))
        self.model = load_model(model_path)
        self.model_path = model_path
        log.info(f"Trained and loaded fresh model: {model_path}")

    def predict_outgoing(self, horizon_days: int = 30) -> pd.DataFrame:
        """
        Прогноз исходящих (спроса) на горизонт days.
        Возвращает DataFrame ['ds','yhat','yhat_lower','yhat_upper'] за будущие дни.
        """
        if self.model is None:
            if self.model_path:
                self._load_with_fallback(self.model_path, self.default_model_path)
        if self.model is None:
            raise RuntimeError("Model not loaded")

        # make_future_dataframe делает naїve timestamps — ок для Prophet
        future = self.model.make_future_dataframe(periods=horizon_days, freq="D")
        forecast = self.model.predict(future)
        self.prediction = forecast.tail(horizon_days)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        return self.prediction

    async def predict_depletion_date(
        self,
        product_id: str,
        warehouse_id: Optional[str] = None,
        horizon_days: int = 30,
        as_of: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Дата истощения (детерминированно): snapshot(as_of) + плановые приходы - прогноз исходящих.
        Возвращает datetime или None, если истощение не попало в горизонт.
        """
        if as_of is None:
            as_of = datetime.utcnow()
        # делаем as_of tz-naive, чтобы сравнения с БД не падали
        if as_of.tzinfo is not None:
            as_of = pd.to_datetime(as_of).tz_localize(None).to_pydatetime()

        # снимок остатков на as_of
        initial_stock = await fetch_snapshot_at(product_id, warehouse_id, as_of)
        if initial_stock is None or initial_stock <= 0:
            # если нет запаса — считаем, что истощение уже сейчас
            return as_of

        # плановые приходы в [as_of, as_of + horizon]
        start = as_of
        end = as_of + timedelta(days=horizon_days)
        planned_incoming = await fetch_planned_incoming(product_id, warehouse_id, start, end)

        # прогноз исходящих на horizon
        predicted_outgoing = self.predict_outgoing(horizon_days)

        # расчёт даты истощения
        return predict_depletion_with_model(initial_stock, planned_incoming, predicted_outgoing)

    def get_predict_as_list(self) -> List[Dict]:
        if self.prediction is None:
            raise RuntimeError("No prediction available. Call predict_outgoing() first.")
        return [
            {
                "ds": pd.to_datetime(row["ds"]).isoformat(),
                "yhat": float(row["yhat"]),
                "yhat_lower": float(row["yhat_lower"]),
                "yhat_upper": float(row["yhat_upper"]),
            }
            for _, row in self.prediction.iterrows()
        ]

    def get_predict_as_dataframe(self) -> pd.DataFrame:
        if self.prediction is None:
            raise RuntimeError("No prediction available. Call predict_outgoing() first.")
        return self.prediction
    
    # app/ml/predictor.py (добавь в класс Predictor)

    def _simulate_depletion(self, initial_stock: float,
                            planned_incoming_df: pd.DataFrame,
                            outgoing_series: pd.Series) -> Optional[datetime]:
        """Имитация: накапливаем stock += incoming - outgoing, ищем первую дату ≤ 0."""
        incoming = (planned_incoming_df.set_index(pd.to_datetime(planned_incoming_df["ds"]))["incoming"]
                    if planned_incoming_df is not None and not planned_incoming_df.empty
                    else pd.Series(dtype=float))
        # общий календарь дат
        parts = []
        if not incoming.empty: parts.append(incoming)
        if not outgoing_series.empty: parts.append(outgoing_series)
        if not parts:
            return None
        all_idx = pd.concat(parts).index.unique().sort_values()

        incoming = incoming.reindex(all_idx, fill_value=0.0)
        outgoing = outgoing_series.reindex(all_idx, fill_value=0.0).clip(lower=0.0)

        stock = float(initial_stock)
        for dt in all_idx:
            stock += float(incoming.get(dt, 0.0))
            stock -= float(outgoing.get(dt, 0.0))
            if stock <= 0:
                # делаем naive (без tz)
                ts = pd.to_datetime(dt).to_pydatetime()
                return ts.replace(tzinfo=None)
        return None

    async def predict_depletion_with_confidence(self,
                                                product_id: str,
                                                warehouse_id: Optional[str],
                                                horizon_days: int = 60,
                                                as_of: Optional[datetime] = None):
        """Возвращает (p50, p10, p90, p_within). p10 — ранняя (быстрая) дата, p90 — поздняя."""
        if as_of is None:
            as_of = datetime.utcnow()
        # делаем naive
        if as_of.tzinfo is not None:
            as_of = as_of.astimezone(tz=None).replace(tzinfo=None)

        initial = await fetch_snapshot_at(product_id, warehouse_id, as_of)
        if initial is None or initial <= 0:
            return None, None, None, None

        start = as_of
        end = as_of + timedelta(days=horizon_days)
        planned_incoming = await fetch_planned_incoming(product_id, warehouse_id, start, end)

        # прогноз исходящих
        forecast = self.predict_outgoing(horizon_days)  # содержит ds,yhat,yhat_lower,yhat_upper
        f = forecast.set_index(pd.to_datetime(forecast["ds"]))
        # Чем выше спрос → тем раньше истощение.
        series_p50 = f["yhat"]
        series_fast = f["yhat_upper"]   # выше расход → раньше (назовём p10)
        series_slow = f["yhat_lower"]   # ниже расход → позже (назовём p90)

        p50 = self._simulate_depletion(initial, planned_incoming, series_p50)
        p10 = self._simulate_depletion(initial, planned_incoming, series_fast)
        p90 = self._simulate_depletion(initial, planned_incoming, series_slow)

        # Простая «достоверность»: 1.0 если даже при низком спросе (p90) истощение в горизонте,
        # 0.5 если только медиана попадает, 0.0 если даже медиана не попала.
        if p90 and p90 <= end:
            p_within = 1.0
        elif p50 and p50 <= end:
            p_within = 0.5
        else:
            p_within = 0.0

        return p50, p10, p90, float(p_within)
