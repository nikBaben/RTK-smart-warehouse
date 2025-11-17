from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from prophet import Prophet
from app.ml.model_store import save_model

def make_synthetic(n_days: int = 365*2, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ds = pd.date_range("2023-01-01", periods=n_days, freq="D")
    # тренд + недельная сезонность + праздники/шум
    trend = 0.02 * np.arange(n_days)           # лёгкий рост
    weekly = 3.0 * np.sin(2*np.pi*ds.dayofweek/7)  # недельный цикл
    spikes = rng.normal(0, 0.5, size=n_days)   # шум
    y = 5 + trend + weekly + spikes
    y = np.clip(y, 0.0, None)                  # неотрицательная отгрузка
    return pd.DataFrame({"ds": ds, "y": y})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/models_store/PROD_DEMO.pkl")
    ap.add_argument("--days", type=int, default=540)
    args = ap.parse_args()

    df = make_synthetic(args.days)
    m = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    m.fit(df)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    save_model(m, args.out)
    print(f"✅ Baseline Prophet saved to {args.out}")

if __name__ == "__main__":
    main()
