import asyncio
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from backend.db.transaction import SqlAlchemyTransaction
from backend.domain.errors import Conflict, InvalidOperation
from backend.models.warehouse import Warehouse
from backend.models.product import Product
from backend.models.user import User
from backend.models.keycloak_user import KeycloakUser
from backend.models.predict import PredictAt
from backend.repositories.warehouse_repo import WarehouseRepository
from backend.repositories.product_repo import ProductRepository
from backend.repositories.user_repo import UserRepository
from backend.repositories.kkid_user_repo import KkidUserRepository
from backend.repositories.predict_repo import PredictRepository
from backend.service.product_service import ProductService
from backend.service.user_service import UserService
from backend.schemas.product import ProductCreate, ProductEdit
from backend.schemas.user import UserCreateWithKeycloak

pytestmark = pytest.mark.integration


def product_service(session):
    return ProductService(
        ProductRepository(session),
        WarehouseRepository(session),
        SqlAlchemyTransaction(session),
    )


def payload(stock=20):
    return ProductCreate(
        name="Part", category="Parts", article="a", stock=stock, warehouse_id="a"
    )


async def seed(sessions):
    async with sessions() as session:
        session.add_all(
            [
                Warehouse(
                    id=id, name=id, address=id, max_products=100, products_count=0
                )
                for id in ["a", "b"]
            ]
        )
        await session.commit()


async def test_repository_flush_does_not_commit(sessions):
    async with sessions() as writer:
        await WarehouseRepository(writer).create(
            id="a", name="a", address="a", max_products=100
        )
        async with sessions() as observer:
            assert await observer.get(Warehouse, "a") is None
        await writer.rollback()
    async with sessions() as observer:
        assert await observer.get(Warehouse, "a") is None


async def test_product_transfer_and_delete_persist_both_counters(sessions):
    await seed(sessions)
    async with sessions() as session:
        service = product_service(session)
        product = await service.create_product(payload())
        pid = product.id
        await service.edit_product(pid, ProductEdit(warehouse_id="b"))
    async with sessions() as session:
        assert (await session.get(Warehouse, "a")).products_count == 0
        assert (await session.get(Warehouse, "b")).products_count == 20
        assert (await session.get(Product, pid)).warehouse_id == "b"
        await product_service(session).delete_product(pid)
    async with sessions() as session:
        assert await session.get(Product, pid) is None
        assert (await session.get(Warehouse, "b")).products_count == 0


async def test_integrity_failure_rolls_back_counter_and_translates_error(sessions):
    await seed(sessions)
    async with sessions() as session:
        service = product_service(session)
        original = ProductRepository.create

        async def invalid_create(repo, **values):
            values["name"] = None  # Real NOT NULL failure after counter update.
            return await original(repo, **values)

        from unittest.mock import patch

        with patch.object(ProductRepository, "create", invalid_create):
            with pytest.raises(InvalidOperation):
                await service.create_product(payload())
    async with sessions() as session:
        assert (await session.get(Warehouse, "a")).products_count == 0
        assert await session.scalar(select(func.count()).select_from(Product)) == 0


async def test_concurrent_additions_cannot_overfill_warehouse(sessions):
    await seed(sessions)

    async def add():
        async with sessions() as session:
            try:
                await product_service(session).create_product(payload(stock=60))
                return "created"
            except InvalidOperation:
                return "full"

    assert sorted(await asyncio.gather(add(), add())) == ["created", "full"]
    async with sessions() as session:
        assert (await session.get(Warehouse, "a")).products_count == 60
        assert await session.scalar(select(func.sum(Product.stock))) == 60


async def test_duplicate_keycloak_link_rolls_back_new_user(sessions):
    async with sessions() as session:
        service = UserService(
            UserRepository(session),
            KkidUserRepository(session),
            SqlAlchemyTransaction(session),
            lambda _: "hashed",
        )
        await service.create_user_with_keycloak(
            UserCreateWithKeycloak(email="a@example.com", name="A", password="x"),
            "same-id",
        )
        with pytest.raises(Conflict):
            await service.create_user_with_keycloak(
                UserCreateWithKeycloak(email="b@example.com", name="B", password="x"),
                "same-id",
            )
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1
        assert await session.scalar(select(func.count()).select_from(KeycloakUser)) == 1
        assert await UserRepository(session).get_by_email("b@example.com") is None


async def test_predictions_are_replaced_atomically(sessions):
    await seed(sessions)
    async with sessions() as session:
        product = await product_service(session).create_product(payload())
        repo = PredictRepository(session)
        now = datetime.now(timezone.utc)
        tx = SqlAlchemyTransaction(session)
        async with tx:
            await repo.save_predictions(
                [(product.id, "a", "Part", now, None, None, 0.8)]
            )
            await tx.commit()
        async with tx:
            await repo.save_predictions(
                [(product.id, "a", "Part", now, None, None, 0.9)]
            )
            await tx.commit()
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(PredictAt)) == 1
        assert (
            await session.scalar(select(PredictAt))
        ).p_deplete_within == pytest.approx(0.9)


async def test_http_routes_use_one_session_and_persist_changes(sessions):
    import httpx
    from backend.main import create_app
    from backend.db.session import get_session

    app = create_app(start_background=False)

    async def override_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/warehouse",
            json={"name": "Warehouse", "address": "Address", "max_products": 100},
        )
        assert response.status_code == 201, response.text
        wid = response.json()["id"]
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Part",
                "article": "sku",
                "category": "Parts",
                "stock": 20,
                "warehouse_id": wid,
            },
        )
        assert response.status_code == 201, response.text
        pid = response.json()["id"]
        response = await client.patch("/api/v1/products/" + pid, json={"stock": 30})
        assert response.status_code == 200, response.text
        assert (await client.get("/api/v1/warehouse/" + wid)).json()[
            "products_count"
        ] == 30
        assert (await client.delete("/api/v1/products/" + pid)).status_code == 200
        assert (await client.get("/api/v1/warehouse/" + wid)).json()[
            "products_count"
        ] == 0


async def test_scheduled_delivery_retry_with_real_database(sessions):
    from backend.repositories.scheduled_delivery_repo import ScheduledDeliveryRepository
    from backend.service.scheduled_delivery_service import ScheduledDeliveryService
    from backend.schemas.scheduled_delivery import ScheduledDeliveryIn

    await seed(sessions)
    async with sessions() as session:
        product = await product_service(session).create_product(payload())
        service = ScheduledDeliveryService(
            ScheduledDeliveryRepository(session),
            ProductRepository(session),
            WarehouseRepository(session),
            SqlAlchemyTransaction(session),
        )
        plan = ScheduledDeliveryIn(
            id="plan",
            product_id=product.id,
            warehouse_id="a",
            scheduled_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            quantity=5,
        )
        assert (await service.create(plan)).id == "plan"
        assert (await service.create(plan)).id == "plan"
        with pytest.raises(Conflict):
            await service.create(plan.model_copy(update={"quantity": 6}))


async def test_delivery_delete_failure_restores_items_in_database(sessions):
    from backend.models.delivery import Delivery
    from backend.models.delivery_items import DeliveryItems
    from backend.repositories.delivery_repo import DeliveryRepository
    from backend.repositories.delivery_items_repo import DeliveryItemsRepository
    from backend.service.delivery_service import DeliveryService
    from backend.schemas.delivery import DeliveryCreate
    from backend.schemas.delivery_items import DeliveryItemsCreate

    await seed(sessions)
    async with sessions() as session:
        repo = DeliveryRepository(session)
        service = DeliveryService(
            repo, DeliveryItemsRepository(session), SqlAlchemyTransaction(session)
        )
        product = await product_service(session).create_product(payload())
        delivery = await service.create_delivery(
            DeliveryCreate(
                id="d",
                name="Delivery",
                warehouse_id="a",
                scheduled_at=datetime.now(timezone.utc),
                quantity=2,
            )
        )
        assert delivery.name == "Delivery"
        item = await service.add_item(
            DeliveryItemsCreate(
                id="i",
                delivery_id="d",
                product_id=product.id,
                warehouse_id="a",
                ordered_quantity=2,
                fact_quantity=0,
            )
        )
        assert item.warehouse_id == "a"
        from unittest.mock import AsyncMock, patch

        with patch.object(
            repo, "delete", AsyncMock(side_effect=RuntimeError("injected failure"))
        ):
            with pytest.raises(RuntimeError):
                await service.delete_delivery("d")
    async with sessions() as session:
        assert await session.get(Delivery, "d") is not None
        assert await session.get(DeliveryItems, "i") is not None


@pytest.mark.parametrize("fail", [False, True])
async def test_scheduler_stock_and_shipment_are_atomic(sessions, fail):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from types import SimpleNamespace
    from unittest.mock import patch
    from backend.scheduler.jobs.create_shipment import run
    from backend.models.shipment import Shipment, ShipmentItems
    from backend.domain.enums import ShipmentStatus

    await seed(sessions)
    async with sessions() as session:
        product = await product_service(session).create_product(payload())
        pid = product.id
        schema = await session.scalar(text("select current_schema()"))
    url = sessions.kw["bind"].url.set(drivername="postgresql+psycopg")

    def run_job():
        engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
        try:
            with Session(engine) as session:
                cfg = SimpleNamespace(
                    shipment_name_prefix="Auto",
                    item_qty_default=3,
                    shipment_status=ShipmentStatus.scheduled,
                )
                if fail:
                    original_flush = session.flush

                    def fail_second_flush(*args, **kwargs):
                        if any(isinstance(item, ShipmentItems) for item in session.new):
                            raise RuntimeError("injected failure")
                        return original_flush(*args, **kwargs)

                    with patch.object(session, "flush", fail_second_flush):
                        with pytest.raises(RuntimeError):
                            run(session, cfg)
                else:
                    run(session, cfg)
                    run(session, cfg)  # same bucket must not create a second shipment
        finally:
            engine.dispose()

    await asyncio.to_thread(run_job)
    async with sessions() as session:
        expected = 20 if fail else 17
        assert (await session.get(Product, pid)).stock == expected
        assert (await session.get(Warehouse, "a")).products_count == expected
        assert await session.scalar(select(func.count()).select_from(Shipment)) == (
            0 if fail else 1
        )
        assert await session.scalar(
            select(func.count()).select_from(ShipmentItems)
        ) == (0 if fail else 1)
