from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from backend.domain.errors import InvalidOperation, NotFound
from backend.schemas.warehouse import WarehouseUpdate
from backend.schemas.robot import RobotCreate
from backend.service.warehouse_service import WarehouseService
from backend.service.robot_service import RobotService
from tests.fakes import Store, MemoryTransaction


async def test_cannot_reduce_capacity_below_current_stock():
    repo = AsyncMock()
    repo.lock_many.return_value = [SimpleNamespace(products_count=20)]
    tx = MemoryTransaction(Store())
    with pytest.raises(InvalidOperation):
        await WarehouseService(repo, tx).edit_warehouse(
            "a", WarehouseUpdate(max_products=10)
        )
    repo.edit_by_id.assert_not_awaited()
    assert tx.commits == 0


async def test_robot_starts_idle_with_full_battery():
    repo, warehouses = AsyncMock(), AsyncMock()
    tx = MemoryTransaction(Store())
    await RobotService(repo, warehouses, tx).create_robot(RobotCreate(warehouse_id="a"))
    values = repo.create.call_args.kwargs
    assert values["status"] == "idle" and values["battery_level"] == 100
    assert values["warehouse_id"] == "a"
    assert tx.commits == 1


async def test_robot_cannot_be_created_for_missing_warehouse():
    repo, warehouses = AsyncMock(), AsyncMock()
    warehouses.get_by_id.return_value = None
    tx = MemoryTransaction(Store())
    with pytest.raises(NotFound):
        await RobotService(repo, warehouses, tx).create_robot(
            RobotCreate(warehouse_id="missing")
        )
    repo.create.assert_not_awaited()
    assert tx.commits == 0


async def test_duplicate_warehouse_name_is_a_service_rule():
    from backend.domain.errors import Conflict
    from backend.schemas.warehouse import WarehouseCreate

    repo = AsyncMock()
    repo.get_by_name.return_value = SimpleNamespace(id="existing")
    tx = MemoryTransaction(Store())
    with pytest.raises(Conflict):
        await WarehouseService(repo, tx).create_warehouse(
            WarehouseCreate(name="Existing", address="Address", max_products=100)
        )
    repo.create.assert_not_awaited()
