from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from backend.domain.errors import Conflict, InvalidOperation
from backend.schemas.scheduled_delivery import ScheduledDeliveryIn
from backend.schemas.delivery_items import DeliveryItemsCreate
from backend.service.scheduled_delivery_service import ScheduledDeliveryService
from backend.service.delivery_service import DeliveryService
from backend.service.shipment_service import ShipmentService
from tests.fakes import Store, MemoryTransaction


def planned(**values):
    data = dict(
        id="plan-1",
        product_id="p",
        warehouse_id="a",
        scheduled_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        quantity=20,
    )
    return ScheduledDeliveryIn(**(data | values))


@pytest.fixture
def scenario():
    repo, products, warehouses = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = None
    products.get.return_value = SimpleNamespace(warehouse_id="a")
    warehouses.get_by_id.return_value = SimpleNamespace(id="a")
    tx = MemoryTransaction(Store())
    return (
        repo,
        products,
        warehouses,
        tx,
        ScheduledDeliveryService(repo, products, warehouses, tx),
    )


async def test_plan_creation_commits(scenario):
    repo, _, _, tx, service = scenario
    await service.create(planned())
    repo.create.assert_awaited_once()
    assert tx.commits == 1


async def test_retry_returns_same_plan_without_inserting(scenario):
    repo, _, _, tx, service = scenario
    existing = SimpleNamespace(**planned().model_dump())
    repo.get.return_value = existing
    assert await service.create(planned()) is existing
    repo.create.assert_not_awaited()


async def test_reused_id_with_different_payload_is_conflict(scenario):
    repo, _, _, tx, service = scenario
    repo.get.return_value = SimpleNamespace(**planned(quantity=99).model_dump())
    with pytest.raises(Conflict):
        await service.create(planned())
    assert tx.commits == 0


async def test_wrong_warehouse_cannot_receive_plan(scenario):
    repo, products, _, tx, service = scenario
    products.get.return_value = SimpleNamespace(warehouse_id="b")
    with pytest.raises(InvalidOperation):
        await service.create(planned())
    repo.create.assert_not_awaited()


async def test_concurrent_retry_is_read_after_rollback(scenario):
    repo, _, _, tx, service = scenario
    existing = SimpleNamespace(**planned().model_dump())
    repo.get.side_effect = [None, existing]
    repo.create.side_effect = Conflict("duplicate")
    assert await service.create(planned()) is existing
    assert tx.rollbacks == 1


async def test_delivery_item_keeps_warehouse_id():
    tx = MemoryTransaction(Store())
    items = AsyncMock()
    service = DeliveryService(AsyncMock(), items, tx)
    await service.add_item(
        DeliveryItemsCreate(
            delivery_id="d",
            product_id="p",
            warehouse_id="a",
            ordered_quantity=2,
            fact_quantity=1,
        )
    )
    assert items.create.call_args.kwargs["warehouse_id"] == "a"
    assert tx.commits == 1


@pytest.mark.parametrize(
    "service_class,kind", [(DeliveryService, "delivery"), (ShipmentService, "shipment")]
)
async def test_delete_parent_and_items_is_one_transaction(service_class, kind):
    tx = MemoryTransaction(Store())
    repo, items = AsyncMock(), AsyncMock()
    repo.get.return_value = SimpleNamespace(id="parent")
    repo.delete.return_value = True
    service = service_class(repo, items, tx)
    assert await getattr(service, "delete_" + kind)("parent")
    getattr(items, "delete_by_" + kind + "_id").assert_awaited_once_with("parent")
    assert tx.commits == 1


@pytest.mark.parametrize(
    "service_class,kind", [(DeliveryService, "delivery"), (ShipmentService, "shipment")]
)
async def test_parent_delete_failure_does_not_commit_items(service_class, kind):
    tx = MemoryTransaction(Store())
    repo, items = AsyncMock(), AsyncMock()
    repo.delete.side_effect = RuntimeError("delete failed")
    with pytest.raises(RuntimeError):
        await getattr(service_class(repo, items, tx), "delete_" + kind)("parent")
    assert tx.commits == 0 and tx.rollbacks == 1
