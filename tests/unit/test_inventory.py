from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from backend.domain.errors import InvalidOperation
from backend.service.inventory_history_service import InventoryHistoryService
from tests.fakes import MemoryTransaction, Store

HEADER = "product_id;product_name;quantity;zone;date\n"


@pytest.fixture
def scenario():
    repo = AsyncMock()
    repo.find_product.return_value = SimpleNamespace(
        id="p", article="sku", category="Parts"
    )
    tx = MemoryTransaction(Store())
    return repo, tx, InventoryHistoryService(repo, tx)


async def test_csv_import_resolves_article_and_commits_once(scenario):
    repo, tx, service = scenario
    await service.import_inventory_from_csv("a", HEADER + "sku;Part;3;A;2026-01-02\n")
    row = repo.add_records.call_args.args[0][0]
    assert row["product_id"] == "p" and row["warehouse_id"] == "a" and row["stock"] == 3
    assert tx.commits == 1


@pytest.mark.parametrize(
    "bad_row",
    [
        "sku;Part;-1;A;2026-01-02",
        "sku;Part;wrong;A;2026-01-02",
        "sku;Part;1;A;not-a-date",
        "sku;;1;A;2026-01-02",
    ],
)
async def test_bad_csv_row_prevents_partial_import(scenario, bad_row):
    repo, tx, service = scenario
    with pytest.raises(InvalidOperation):
        await service.import_inventory_from_csv(
            "a", HEADER + "sku;Part;2;A;2026-01-02\n" + bad_row
        )
    repo.add_records.assert_not_awaited()
    assert tx.commits == 0


async def test_unknown_product_prevents_import(scenario):
    repo, tx, service = scenario
    repo.find_product.return_value = None
    with pytest.raises(InvalidOperation):
        await service.import_inventory_from_csv(
            "a", HEADER + "missing;Part;1;A;2026-01-02"
        )
    repo.add_records.assert_not_awaited()


async def test_missing_headers_are_reported(scenario):
    repo, tx, service = scenario
    with pytest.raises(InvalidOperation, match="CSV"):
        await service.import_inventory_from_csv("a", "garbage\n123")
    repo.add_records.assert_not_awaited()
