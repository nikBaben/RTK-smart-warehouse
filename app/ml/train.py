import argparse
import asyncio
from typing import Optional
import pandas as pd
from prophet import Prophet

from app.ml.data_access import fetch_outgoing_timeseries
from app.ml.model_store import save_model


async def train_for_product(
    product_id: str,
    model_path: str,
    freq: str = "D",
    warehouse_id: Optional[str] = None,
):
    # Загружаем временной ряд отгрузок
    df = await fetch_outgoing_timeseries(product_id, warehouse_id, None, None, freq=freq)

    if df.empty or len(df) < 10:
        raise RuntimeError("Not enough data to train model. Need at least 10 dates")

    train_df = df.copy()

    train_df["ds"] = pd.to_datetime(train_df["ds"], utc=True).dt.tz_localize(None)
    train_df["y"] = train_df["y"].astype(float)

    m = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    m.add_country_holidays("RU")
    m.fit(train_df)

    save_model(m, model_path)
    print(f"✅ Model trained and saved to: {model_path}")
    return model_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--freq", default="D")
    parser.add_argument("--warehouse-id", default=None)
    args = parser.parse_args()

    asyncio.run(
        train_for_product(
            args.product_id,
            args.model_path,
            args.freq,
            args.warehouse_id,
        )
    )


if __name__ == "__main__":
    main()