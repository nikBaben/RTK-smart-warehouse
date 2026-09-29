from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from backend.domain.errors import InvalidOperation, NotFound
from backend.schemas.product import ProductCreate, ProductEdit
from backend.service.product_service import ProductService
from tests.fakes import Store, Warehouses, Products, MemoryTransaction


@pytest.fixture
def scenario():
    store = Store()
    store.warehouses = {
        id: SimpleNamespace(id=id, max_products=100, products_count=0)
        for id in ["a", "b"]
    }
    transaction = MemoryTransaction(store)
    return (
        store,
        transaction,
        ProductService(Products(store), Warehouses(store), transaction),
    )


def payload(**changes):
    return ProductCreate(
        **dict(
            dict(
                name="Widget",
                category="Parts",
                article="sku",
                stock=20,
                warehouse_id="a",
            ),
            **changes,
        )
    )


async def test_create_updates_capacity_and_commits_once(scenario):
    store, tx, service = scenario
    product = await service.create_product(payload())
    assert store.warehouses["a"].products_count == 20
    assert store.products[product.id].min_stock == 4
    assert tx.commits == 1


async def test_capacity_failure_changes_nothing(scenario):
    store, tx, service = scenario
    with pytest.raises(InvalidOperation):
        await service.create_product(payload(stock=101))
    assert not store.products
    assert store.warehouses["a"].products_count == 0
    assert tx.commits == 0


async def test_transfer_without_stock_change_updates_both_warehouses(scenario):
    store, tx, service = scenario
    product = await service.create_product(payload())
    await service.edit_product(product.id, ProductEdit(warehouse_id="b"))
    assert store.warehouses["a"].products_count == 0
    assert store.warehouses["b"].products_count == 20
    assert store.products[product.id].warehouse_id == "b"


async def test_failed_transfer_restores_source_stock(scenario):
    store, tx, service = scenario
    product = await service.create_product(payload())
    store.warehouses["b"].products_count = 95
    with pytest.raises(InvalidOperation):
        await service.edit_product(product.id, ProductEdit(warehouse_id="b"))
    assert store.warehouses["a"].products_count == 20
    assert store.warehouses["b"].products_count == 95
    assert store.products[product.id].warehouse_id == "a"
    assert tx.commits == 1


async def test_stock_patch_only_changes_stock(scenario):
    store, tx, service = scenario
    product = await service.create_product(payload())
    await service.edit_product(product.id, ProductEdit(stock=0))
    assert store.warehouses["a"].products_count == 0
    assert store.products[product.id].category == "Parts"


async def test_delete_frees_capacity(scenario):
    store, tx, service = scenario
    product = await service.create_product(payload())
    await service.delete_product(product.id)
    assert not store.products
    assert store.warehouses["a"].products_count == 0
    assert tx.commits == 2


async def test_commit_failure_rolls_back_product_and_counter(scenario):
    store, tx, service = scenario
    tx.fail_commit = True
    with pytest.raises(RuntimeError):
        await service.create_product(payload())
    assert not store.products
    assert store.warehouses["a"].products_count == 0


@pytest.mark.parametrize("operation", ["edit", "delete"])
async def test_missing_product_is_explicit_not_found(scenario, operation):
    _, tx, service = scenario
    with pytest.raises(NotFound):
        if operation == "edit":
            await service.edit_product("missing", ProductEdit(stock=1))
        else:
            await service.delete_product("missing")
    assert tx.commits == 0


async def test_missing_warehouse_is_not_found(scenario):
    _, tx, service = scenario
    with pytest.raises(NotFound):
        await service.create_product(payload(warehouse_id="missing"))
    assert tx.commits == 0


def test_negative_stock_rejected():
    with pytest.raises(ValidationError):
        ProductEdit(stock=-1)


async def test_cancelled_operation_rolls_back(scenario):
    import asyncio
    from unittest.mock import AsyncMock

    store, tx, service = scenario
    service.repo.create = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await service.create_product(payload())
    assert store.warehouses["a"].products_count == 0
    assert not store.products
    assert tx.commits == 0 and tx.rollbacks == 1
