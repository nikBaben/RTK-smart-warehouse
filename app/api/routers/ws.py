from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path,Depends
from app.ws.ws_manager import manager
from app.db.session import async_session
from app.ws.battery_events import publish_robot_avg_snapshot
from app.ws.inventory_critical_streamer import publish_critical_unique_articles_snapshot
from app.ws.inventory_scans_streamer import publish_inventory_scanned_24h_snapshot
from app.ws.inventory_status import publish_status_avg_snapshot
from app.ws.products_events import publish_product_snapshot
from app.events.bus import get_bus_for_current_loop, ROBOT_CH
from app.ws.robot_status_count_streamer import publish_robot_status_count_snapshot
from app.ws.robot_activity_streamer import publish_robot_activity_series_from_history
from app.ws.product_scan_publisher import publish_initial_product_scan_unicast
from app.repositories.product_repo import ProductRepository
from app.repositories.robot_history_repo import RobotHistoryRepository
from app.repositories.inventory_history_repo import InventoryHistoryRepository
from app.repositories.robot_repo import RobotRepository
from app.api.deps import get_product_repo,get_robot_history_repo,get_inventory_history_repo,get_robot_repo

router = APIRouter()

@router.websocket("/ws/warehouses/{warehouse_id}")
async def ws_warehouse(
    ws: WebSocket, 
    warehouse_id: str,
    repo: ProductRepository = Depends(get_product_repo),
    repo_robot_history: RobotHistoryRepository = Depends(get_robot_history_repo),
    repo_inventory_history: InventoryHistoryRepository = Depends(get_inventory_history_repo),
    repo_robot: RobotRepository = Depends(get_robot_repo)
    ):
    session_id = await manager.connect(ws, warehouse_id)
    try:
        await publish_robot_avg_snapshot(repo_robot, warehouse_id)
        await publish_critical_unique_articles_snapshot(repo_inventory_history, warehouse_id)
        await publish_inventory_scanned_24h_snapshot(repo_inventory_history, warehouse_id)
        await publish_status_avg_snapshot(repo, warehouse_id)
        await publish_product_snapshot(repo, warehouse_id)
        await publish_robot_activity_series_from_history(repo_robot_history, warehouse_id, force=True)
        await publish_robot_status_count_snapshot(repo_robot, warehouse_id)
        await publish_initial_product_scan_unicast(repo_inventory_history, warehouse_id, session_id)
        while True:
            await ws.receive_text()  
    except WebSocketDisconnect:
        await manager.disconnect(ws)
