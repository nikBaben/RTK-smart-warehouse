from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pandas as pd

from backend.ml.predictor import Predictor


def test_saved_model_forecasts_from_requested_date_not_training_end():
    model = Mock()
    model.predict.side_effect = lambda frame: frame.assign(
        yhat=2, yhat_lower=1, yhat_upper=3
    )
    predictor = Predictor(model=model)
    forecast = predictor.predict_outgoing(
        horizon_days=3,
        as_of=datetime(2026, 9, 28, 1, tzinfo=timezone(timedelta(hours=3))),
    )
    assert forecast["ds"].tolist() == list(pd.date_range("2026-09-28", periods=3))
    model.make_future_dataframe.assert_not_called()
