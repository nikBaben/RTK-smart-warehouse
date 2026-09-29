from datetime import datetime, timezone

import httpx
import pytest

from backend.db.session import get_session
from backend.main import create_app
from backend.models.robot import Robot
from backend.models.warehouse import Warehouse

pytestmark = pytest.mark.integration


async def test_robot_list_serializes_timestamps_and_filters_by_warehouse(sessions):
    updated_at = datetime(2026, 1, 2, 12, 30, tzinfo=timezone.utc)
    async with sessions() as session:
        session.add_all(
            Warehouse(id=wid, name=wid, address=wid, max_products=100)
            for wid in ("a", "b")
        )
        await session.flush()
        session.add_all(
            Robot(id=rid, warehouse_id=wid, last_update=updated_at)
            for rid, wid in (("R001", "a"), ("R002", "b"))
        )
        await session.commit()

    app = create_app(start_background=False)

    async def override_session():
        # A fresh session must load every response field from the database.
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/robot/get_robots_by_warehouse_id/a")
        assert response.status_code == 200, response.text
        robots = response.json()
        assert len(robots) == 1
        robot = robots[0]
        assert robot["id"] == "R001"
        assert robot["warehouse_id"] == "a"
        assert datetime.fromisoformat(robot["last_update"]) == updated_at
        assert datetime.fromisoformat(robot["created_at"]).tzinfo is not None
        assert robot["status"] == "idle"
        assert robot["battery_level"] == 100
        assert robot["current_zone"] == "Хранение"
        assert robot["current_row"] == 0
        assert robot["current_shelf"] == 0
