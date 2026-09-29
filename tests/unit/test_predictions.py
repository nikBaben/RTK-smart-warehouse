from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from backend.service.predict_service import PredictService
from tests.fakes import MemoryTransaction, Store


async def test_prediction_factory_and_persistence_are_replaceable():
    repo, products, warehouses = AsyncMock(), AsyncMock(), AsyncMock()
    products.get_name.return_value = "Part"
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    predictor = AsyncMock()
    predictor.predict_depletion_with_confidence.return_value = (now, None, None, 0.8)
    factory = Mock(return_value=predictor)
    tx = MemoryTransaction(Store())
    result = await PredictService(
        repo, products, warehouses, tx, factory
    ).rebuild_prediction_for_product("a", "p")
    assert result["persisted"] is True and result["product_name"] == "Part"
    assert tx.commits == 1
    assert repo.save_predictions.call_args.args[0][0][:3] == ("p", "a", "Part")


async def test_no_depletion_does_not_save_fictional_prediction():
    repo, products, warehouses = AsyncMock(), AsyncMock(), AsyncMock()
    products.get_name.return_value = "Part"
    predictor = AsyncMock()
    predictor.predict_depletion_with_confidence.return_value = (None, None, None, None)
    tx = MemoryTransaction(Store())
    result = await PredictService(
        repo, products, warehouses, tx, lambda **_: predictor
    ).rebuild_prediction_for_product("a", "p")
    assert result["persisted"] is False
    repo.save_predictions.assert_not_awaited()
    assert tx.commits == 0
