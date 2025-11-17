from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

log = logging.getLogger("ml.predictor")

from app.ml.data_access import (
    fetch_outgoing_timeseries,
    fetch_snapshot_at,
    fetch_planned_incoming,
)
from app.ml.model_store import save_model, load_model_any

try:
    from prophet import Prophet  # type: ignore
except Exception:  # pragma: no cover
    Prophet = None  # type: ignore


def _to_utc_naive(dt: datetime) -> datetime:
    dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


class Predictor:
    """
    Персональная модель -> fallback default -> on-the-fly Prophet.
    Возвращает дату истощения и, при необходимости, доверительные интервалы.
    """

    def __init__(self, model_path: str, default_model_path: Optional[str] = None):
        self.model_path = Path(model_path)
        self.default_model_path = Path(default_model_path) if default_model_path else None
        self.model: Optional[Any] = None
        self._train_ctx: Optional[Dict[str, Any]] = None

    # -------------------- загрузка / обучение --------------------

    async def _load_async(self) -> None:
        """
        Алгоритм:
        1) Если есть персональная модель -> пробуем загрузить. Если неподходящая (нет .predict) — игнорируем.
        2) Иначе пытаемся загрузить fallback.
        3) Если и fallback нет — обучаем on-the-fly реальную Prophet-модель и сохраняем.
        """
        # 1) персональная
        if self.model_path.exists():
            try:
                self.model = load_model_any(str(self.model_path))
                log.info("Загружена персональная модель: %s (%s)", self.model_path, type(self.model))
                if not hasattr(self.model, "predict"):
                    log.warning("Персональная модель не поддерживает predict(); игнорирую и перехожу к fallback.")
                    self.model = None
            except Exception as e:
                log.warning("Не удалось загрузить персональную модель %s: %s", self.model_path, e)
                self.model = None

        # 2) fallback
        if self.model is None and self.default_model_path and self.default_model_path.exists():
            try:
                self.model = load_model_any(str(self.default_model_path))
                log.info("Загружена fallback-модель: %s (%s)", self.default_model_path, type(self.model))
                if not hasattr(self.model, "predict"):
                    log.warning("Fallback-модель не поддерживает predict(); буду обучать on-the-fly.")
                    self.model = None
            except Exception as e:
                log.warning("Не удалось загрузить fallback-модель %s: %s", self.default_model_path, e)
                self.model = None

        # 3) on-the-fly
        if self.model is None:
            log.warning("Model %s not found/usable and no valid fallback. Training on the fly...", self.model_path)
            await self._train_and_store(self.model_path)
            if self.model_path.exists():
                try:
                    self.model = load_model_any(str(self.model_path))
                    log.info("On-the-fly модель обучена и загружена: %s", self.model_path)
                except Exception as e:
                    log.error("On-the-fly модель сохранена, но не загружается: %s", e)
                    self.model = None

    async def _train_and_store(self, target_path: Path) -> None:
        """
        Реальное on-the-fly обучение Prophet по отгрузкам товара.
        Требует self._train_ctx c product_id, warehouse_id, freq.
        Сохраняем через joblib (см. model_store).
        """
        ctx = self._train_ctx or {}
        product_id: Optional[str] = ctx.get("product_id")
        warehouse_id: Optional[str] = ctx.get("warehouse_id")
        freq: str = ctx.get("freq", "D")

        if Prophet is None:
            log.warning("Prophet недоступен — пропускаю on-the-fly обучение.")
            return
        if not product_id:
            log.warning("Нет product_id в train_ctx — пропускаю on-the-fly обучение.")
            return

        try:
            df = await fetch_outgoing_timeseries(
                product_id=product_id,
                warehouse_id=warehouse_id,
                start=None,
                end=None,
                freq=freq,
            )
        except Exception as e:  # pragma: no cover
            log.exception("Не удалось получить временной ряд отгрузок для обучения: %s", e)
            return

        if df is None or df.empty or len(df) < 10:
            log.warning("Недостаточно данных для on-the-fly обучения (%s): %s точек.", product_id, 0 if df is None else len(df))
            return

        train_df = df.copy()
        train_df["ds"] = pd.to_datetime(train_df["ds"]).dt.tz_localize(None)
        train_df["y"] = train_df["y"].astype(float)

        try:
            # interval_width=0.8 даст надежные lower/upper -> пригодятся для P10/P90
            m = Prophet(yearly_seasonality=True, weekly_seasonality=True, interval_width=0.8)
            # при желании: m.add_country_holidays("RU")
            m.fit(train_df)
            save_model(m, str(target_path))
            log.info("On-the-fly модель обучена и сохранена: %s", target_path)
        except Exception as e:  # pragma: no cover
            log.exception("Ошибка обучения/сохранения Prophet: %s", e)

    # -------------------- публичная загрузка --------------------

    def load(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            raise RuntimeError("Predictor.load() вызван из активного event loop. Используйте `await predictor.load_async()`.")
        else:
            asyncio.run(self._load_async())

    async def load_async(self) -> None:
        await self._load_async()

    # -------------------- утилиты для симуляции --------------------

    @staticmethod
    def _simulate_depletion(
        current_stock: float,
        outgoing: pd.Series,
        incoming: pd.Series,
    ) -> Optional[datetime]:
        stock = float(current_stock)
        for ds, out in outgoing.sort_index().items():
            inc = float(incoming.get(ds, 0.0))
            stock += inc
            stock -= float(out)
            if stock <= 0:
                return pd.to_datetime(ds).to_pydatetime().replace(tzinfo=timezone.utc)
        return None

    # -------------------- инференс --------------------

    async def predict_depletion_date(
        self,
        product_id: str,
        warehouse_id: Optional[str],
        horizon_days: int,
        as_of: Optional[datetime] = None,
        freq: str = "D",
    ) -> Optional[datetime]:
        """
        P50 (медианная) дата истощения.
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        as_of_naive_utc = _to_utc_naive(as_of)

        # контекст on-the-fly
        self._train_ctx = {"product_id": product_id, "warehouse_id": warehouse_id, "freq": freq}
        if self.model is None:
            await self._load_async()
        if self.model is None or not hasattr(self.model, "predict"):
            log.warning("Нет пригодной модели для прогноза (product_id=%s): верну None.", product_id)
            return None

        current_stock = await fetch_snapshot_at(
            product_id=product_id,
            warehouse_id=warehouse_id,
            at_time=as_of,
        )
        if current_stock is None:
            log.warning("Нет снимка остатков для товара %s / склада %s", product_id, warehouse_id)
            return None

        end = as_of_naive_utc + timedelta(days=horizon_days)
        incoming_df = await fetch_planned_incoming(
            product_id=product_id,
            warehouse_id=warehouse_id,
            start=as_of_naive_utc,
            end=end,
            freq=freq,
        )
        if incoming_df is None or incoming_df.empty:
            incoming_df = pd.DataFrame({"ds": [], "incoming": []})
        incoming_df["ds"] = pd.to_datetime(incoming_df["ds"]).dt.tz_localize(None)
        incoming_df = incoming_df.set_index("ds")["incoming"].astype(float)

        future = pd.DataFrame({"ds": pd.date_range(as_of_naive_utc + timedelta(days=1), end, freq=freq)})
        if future.empty:
            return None
        future["ds"] = pd.to_datetime(future["ds"]).dt.tz_localize(None)

        forecast = self.model.predict(future)
        if "yhat" not in forecast.columns:
            log.warning("Прогноз модели не содержит yhat (product_id=%s)", product_id)
            return None

        outgoing_p50 = forecast.set_index("ds")["yhat"].clip(lower=0.0)
        return self._simulate_depletion(current_stock, outgoing_p50, incoming_df)

    async def predict_depletion_with_confidence(
        self,
        product_id: str,
        warehouse_id: Optional[str],
        horizon_days: int,
        as_of: Optional[datetime] = None,
        freq: str = "D",
        within_days: Optional[int] = None,
    ) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime], Optional[float]]:
        """
        Возвращает (P50, P10, P90, p_deplete_within).
        P10 — «ранняя» дата (используем более высокий спрос => yhat_upper),
        P90 — «поздняя» дата (используем более низкий спрос => yhat_lower).
        p_deplete_within — вероятность истощения за within_days (если передан), иначе None.
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        as_of_naive_utc = _to_utc_naive(as_of)

        # контекст on-the-fly
        self._train_ctx = {"product_id": product_id, "warehouse_id": warehouse_id, "freq": freq}
        if self.model is None:
            await self._load_async()
        if self.model is None or not hasattr(self.model, "predict"):
            log.warning("Нет пригодной модели для прогноза (product_id=%s): верну None.", product_id)
            return (None, None, None, None)

        current_stock = await fetch_snapshot_at(product_id, warehouse_id, at_time=as_of)
        if current_stock is None:
            log.warning("Нет снимка остатков для товара %s / склада %s", product_id, warehouse_id)
            return (None, None, None, None)

        end = as_of_naive_utc + timedelta(days=horizon_days)
        incoming_df = await fetch_planned_incoming(product_id, warehouse_id, start=as_of_naive_utc, end=end, freq=freq)
        if incoming_df is None or incoming_df.empty:
            incoming_df = pd.DataFrame({"ds": [], "incoming": []})
        incoming_df["ds"] = pd.to_datetime(incoming_df["ds"]).dt.tz_localize(None)
        incoming_s = incoming_df.set_index("ds")["incoming"].astype(float)

        future = pd.DataFrame({"ds": pd.date_range(as_of_naive_utc + timedelta(days=1), end, freq=freq)})
        if future.empty:
            return (None, None, None, None)
        future["ds"] = pd.to_datetime(future["ds"]).dt.tz_localize(None)

        forecast = self.model.predict(future)
        cols = forecast.columns
        if not {"yhat", "yhat_lower", "yhat_upper"}.issubset(set(cols)):
            # если модель обучена без интервалов — вернём только p50
            outgoing_p50 = forecast.set_index("ds")["yhat"].clip(lower=0.0)
            p50 = self._simulate_depletion(current_stock, outgoing_p50, incoming_s)
            return (p50, None, None, None)

        f = forecast.set_index("ds")
        outgoing_p50 = f["yhat"].clip(lower=0.0)
        outgoing_p10 = f["yhat_upper"].clip(lower=0.0)  # большая отгрузка -> раньше исчерпание
        outgoing_p90 = f["yhat_lower"].clip(lower=0.0)  # меньшая отгрузка -> позже исчерпание

        p50 = self._simulate_depletion(current_stock, outgoing_p50, incoming_s)
        p10 = self._simulate_depletion(current_stock, outgoing_p10, incoming_s)
        p90 = self._simulate_depletion(current_stock, outgoing_p90, incoming_s)

        # простая оценка p(deplete within N days): доля квантилей, истощающихся раньше дедлайна
        prob_within: Optional[float] = None
        if within_days is not None:
            deadline = (as_of_naive_utc + timedelta(days=within_days)).replace(tzinfo=timezone.utc)
            paths = [p for p in [p10, p50, p90] if p is not None]
            if paths:
                prob_within = sum(1 for d in paths if d <= deadline) / len(paths)

        return (p50, p10, p90, prob_within)