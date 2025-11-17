from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.ws.ws_manager import manager

# Паблишеры
from app.ws.battery_events import publish_robot_avg_snapshot
from app.ws.inventory_critical_streamer import publish_critical_unique_articles_snapshot
from app.ws.inventory_scans_streamer import publish_inventory_scanned_24h_snapshot
from app.ws.inventory_status import publish_status_avg_snapshot
from app.ws.products_events import publish_product_snapshot
from app.ws.robot_status_count_streamer import publish_robot_status_count_snapshot
from app.ws.robot_activity_streamer import publish_robot_activity_series_from_history
from app.ws.product_scan_publisher import publish_initial_product_scan_unicast  # проверь, что файл именно так называется

# Репозитории через DI
from app.repositories.product_repo import ProductRepository
from app.repositories.robot_history_repo import RobotHistoryRepository
from app.repositories.inventory_history_repo import InventoryHistoryRepository
from app.repositories.robot_repo import RobotRepository
from app.api.deps import (
    get_product_repo,
    get_robot_history_repo,
    get_inventory_history_repo,
    get_robot_repo,
)

router = APIRouter()


@router.websocket("/ws/warehouses/{warehouse_id}")
async def ws_warehouse(
    ws: WebSocket,
    warehouse_id: str,
    repo: ProductRepository = Depends(get_product_repo),
    repo_robot_history: RobotHistoryRepository = Depends(get_robot_history_repo),
    repo_inventory_history: InventoryHistoryRepository = Depends(get_inventory_history_repo),
    repo_robot: RobotRepository = Depends(get_robot_repo),
):
    session_id = await manager.connect(ws, warehouse_id)
    try:
        # 1) Любые вызовы, использующие ОДНУ и ту же сессию/репозиторий (repo) — последовательно.
        #    ВАЖНО: отключаем пересчёт статусов в рамках WS-сессии.
        try:
            await publish_product_snapshot(
                repo,
                warehouse_id,
                recompute_before_publish=False,  # <-- вот ключевая правка
            )
        except Exception as e:
            print(f"[ws_init] publish_product_snapshot error: {e}")

        try:
            await publish_status_avg_snapshot(repo, warehouse_id)
        except Exception as e:
            print(f"[ws_init] publish_status_avg_snapshot error: {e}")

        # 2) Остальные публикации можно параллелить — они используют другие репозитории/сессии.
        results = await asyncio.gather(
            publish_robot_avg_snapshot(repo_robot, warehouse_id),
            publish_critical_unique_articles_snapshot(repo_inventory_history, warehouse_id),
            publish_inventory_scanned_24h_snapshot(repo_inventory_history, warehouse_id),
            publish_robot_activity_series_from_history(repo_robot_history, warehouse_id, force=True),
            publish_robot_status_count_snapshot(repo_robot, warehouse_id),
            publish_initial_product_scan_unicast(repo_inventory_history, warehouse_id, session_id),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                print(f"[ws_init] publish error: {r}")

        # 3) Держим соединение открытым
        while True:
            await ws.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await manager.disconnect(ws)
        except Exception:
            pass
