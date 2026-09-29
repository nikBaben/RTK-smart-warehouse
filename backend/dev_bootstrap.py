"""Local development setup; invoked only by compose.dev.yaml's one-shot service."""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from backend.core.config import settings
from backend.db.session import async_session, get_engine
from backend.models.delivery import Delivery, ScheduledDelivery
from backend.models.delivery_items import DeliveryItems
from backend.models.inventory_history import InventoryHistory
from backend.models.product import Product
from backend.models.robot import Robot
from backend.models.shipment import Shipment, ShipmentItems
from backend.models.warehouse import Warehouse


def prepare_keycloak() -> None:
    """Create missing local resources, preserving existing users and passwords."""
    with httpx.Client(base_url=settings.KEYCLOAK_URL.rstrip("/"), timeout=30) as client:
        response = client.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": os.environ["KC_BOOTSTRAP_ADMIN_USERNAME"],
                "password": os.environ["KC_BOOTSTRAP_ADMIN_PASSWORD"],
            },
        )
        response.raise_for_status()
        client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
        realm = f"/admin/realms/{settings.KEYCLOAK_REALM}"
        response = client.get(realm)
        if response.status_code == 404:
            client.post(
                "/admin/realms",
                json={
                    "realm": settings.KEYCLOAK_REALM,
                    "enabled": True,
                    "registrationAllowed": False,
                    "loginWithEmailAllowed": True,
                },
            ).raise_for_status()
        else:
            response.raise_for_status()

        response = client.get(f"{realm}/roles/admin")
        if response.status_code == 404:
            client.post(f"{realm}/roles", json={"name": "admin"}).raise_for_status()
        else:
            response.raise_for_status()

        response = client.get(
            f"{realm}/clients", params={"clientId": settings.KEYCLOAK_CLIENT_ID}
        )
        response.raise_for_status()
        if not response.json():
            client.post(
                f"{realm}/clients",
                json={
                    "clientId": settings.KEYCLOAK_CLIENT_ID,
                    "secret": settings.KEYCLOAK_CLIENT_SECRET,
                    "enabled": True,
                    "publicClient": False,
                    "standardFlowEnabled": False,
                    "directAccessGrantsEnabled": True,
                    "defaultClientScopes": [
                        "web-origins",
                        "acr",
                        "roles",
                        "profile",
                        "email",
                    ],
                    "protocolMappers": [
                        {
                            "name": "Application roles in userinfo",
                            "protocol": "openid-connect",
                            "protocolMapper": "oidc-usermodel-realm-role-mapper",
                            "config": {
                                "claim.name": "realm_access.roles",
                                "jsonType.label": "String",
                                "multivalued": "true",
                                "userinfo.token.claim": "true",
                                "access.token.claim": "true",
                                "id.token.claim": "true",
                            },
                        }
                    ],
                },
            ).raise_for_status()

        def ensure_user(
            username: str, password: str, email: str, first_name: str
        ) -> str:
            result = client.get(
                f"{realm}/users", params={"username": username, "exact": "true"}
            )
            result.raise_for_status()
            if result.json():
                return result.json()[0]["id"]
            result = client.post(
                f"{realm}/users",
                json={
                    "username": username,
                    "email": email,
                    "enabled": True,
                    "emailVerified": True,
                    "firstName": first_name,
                    "lastName": "Локальный",
                    "requiredActions": [],
                    "credentials": [
                        {"type": "password", "value": password, "temporary": False}
                    ],
                },
            )
            result.raise_for_status()
            return result.headers["Location"].rstrip("/").split("/")[-1]

        admin_id = ensure_user(
            settings.KEYCLOAK_ADMIN_USERNAME,
            settings.KEYCLOAK_ADMIN_PASSWORD,
            "service-admin@example.com",
            "Сервис",
        )
        result = client.get(f"{realm}/clients", params={"clientId": "realm-management"})
        result.raise_for_status()
        management_id = result.json()[0]["id"]
        result = client.get(f"{realm}/clients/{management_id}/roles/realm-admin")
        result.raise_for_status()
        client.post(
            f"{realm}/users/{admin_id}/role-mappings/clients/{management_id}",
            json=[result.json()],
        ).raise_for_status()

        email = os.environ["DEV_LOGIN_EMAIL"]
        user_id = ensure_user(
            email, os.environ["DEV_LOGIN_PASSWORD"], email, "Администратор"
        )
        result = client.get(f"{realm}/roles/admin")
        result.raise_for_status()
        client.post(
            f"{realm}/users/{user_id}/role-mappings/realm", json=[result.json()]
        ).raise_for_status()
    print("Dev Keycloak is ready (existing passwords preserved).", flush=True)


async def seed_warehouse() -> None:
    """Seed an empty application database once; never reset user changes on restart."""
    now = datetime.now(timezone.utc)
    async with async_session() as session, session.begin():
        if await session.scalar(select(Warehouse.id).limit(1)) is not None:
            print("Warehouse data already exists; skipping demo seed.", flush=True)
            return
        session.add_all(
            [
                Warehouse(
                    id="DEV-WH-1",
                    name="Демонстрационный склад",
                    address="Москва, Складская улица, 1",
                    max_products=1000,
                    products_count=180,
                    row_x=6,
                    row_y=6,
                ),
                Warehouse(
                    id="DEV-WH-2",
                    name="Резервный склад",
                    address="Москва, Складская улица, 2",
                    max_products=500,
                    products_count=0,
                    row_x=6,
                    row_y=6,
                ),
            ]
        )
        await session.flush()
        robot = Robot(
            id="DEV1", warehouse_id="DEV-WH-1", status="idle", battery_level=100
        )
        session.add(robot)
        products = [
            Product(
                id="DEV-P-1",
                name="Wi-Fi роутер",
                category="Сетевое оборудование",
                article="RT-001",
                warehouse_id="DEV-WH-1",
                stock=120,
                min_stock=20,
                optimal_stock=150,
                current_row=1,
                current_shelf="A",
                status="ok",
            ),
            Product(
                id="DEV-P-2",
                name="Оптический терминал",
                category="Сетевое оборудование",
                article="RT-002",
                warehouse_id="DEV-WH-1",
                stock=50,
                min_stock=20,
                optimal_stock=80,
                current_row=2,
                current_shelf="B",
                status="ok",
            ),
            Product(
                id="DEV-P-3",
                name="Патч-корд",
                category="Кабели",
                article="RT-003",
                warehouse_id="DEV-WH-1",
                stock=10,
                min_stock=20,
                optimal_stock=100,
                current_row=3,
                current_shelf="C",
                status="critical",
            ),
        ]
        session.add_all(products)
        await session.flush()
        for day in range(30):
            at = now - timedelta(days=30 - day)
            shipment_id = f"DEV-S-{day}"
            session.add(
                Shipment(
                    id=shipment_id,
                    name="Демонстрационная отгрузка",
                    warehouse_id="DEV-WH-1",
                    scheduled_at=at,
                    shipped_at=at,
                    quantity=6,
                    status="shipped",
                    created_at=at,
                )
            )
            await session.flush()
            for product in products:
                session.add(
                    ShipmentItems(
                        id=f"{shipment_id}-{product.id}",
                        shipment_id=shipment_id,
                        product_id=product.id,
                        warehouse_id=product.warehouse_id,
                        ordered_quantity=2,
                        fact_quantity=2,
                        created_at=at,
                    )
                )
                session.add(
                    InventoryHistory(
                        id=f"DEV-H-{day}-{product.id}",
                        product_id=product.id,
                        robot_id=robot.id,
                        warehouse_id=product.warehouse_id,
                        name=product.name,
                        category=product.category,
                        article=product.article,
                        stock=product.stock + (30 - day) * 2,
                        min_stock=product.min_stock,
                        optimal_stock=product.optimal_stock,
                        current_zone="Хранение",
                        current_row=product.current_row,
                        current_shelf=product.current_shelf,
                        status="ok",
                        created_at=at,
                    )
                )
        session.add(
            Delivery(
                id="DEV-D-1",
                name="Демонстрационная поставка",
                warehouse_id="DEV-WH-1",
                scheduled_at=now - timedelta(days=31),
                delivered_at=now - timedelta(days=31),
                quantity=360,
                status="arrived",
                supplier="Демо-поставщик",
            )
        )
        await session.flush()
        for product in products:
            session.add(
                DeliveryItems(
                    id=f"DEV-D-{product.id}",
                    delivery_id="DEV-D-1",
                    product_id=product.id,
                    warehouse_id=product.warehouse_id,
                    ordered_quantity=product.stock + 60,
                    fact_quantity=product.stock + 60,
                )
            )
        session.add(
            ScheduledDelivery(
                id="DEV-PLAN-1",
                product_id="DEV-P-3",
                warehouse_id="DEV-WH-1",
                scheduled_at=now + timedelta(days=2),
                quantity=90,
                status="scheduled",
                supplier="Демо-поставщик",
            )
        )
    print("Demo warehouses, products, robot and operation history created.", flush=True)


async def main() -> None:
    if os.environ.get("DEV_BOOTSTRAP") != "1":
        raise RuntimeError("Dev bootstrap can only run in the dev-init container.")
    prepare_keycloak()
    try:
        await seed_warehouse()
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
