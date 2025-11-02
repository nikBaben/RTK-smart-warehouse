# app/ws/initial_product_scan_publisher.py
from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH

LAST_SCANS_LIMIT = int(os.getenv("LAST_SCANS_LIMIT", "20"))
REDIS_DSN = os.getenv("REDIS_DSN", "redis://myapp-redis:6379/0")

try:
    import redis.asyncio as aioredis  # redis>=4.2
except Exception:
    import aioredis  # type: ignore


class InventoryHistoryRepoProto(Protocol):
    async def get_last_scans(self, warehouse_id: str, limit: int) -> List[Any]: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ih_row_to_payload(row: dict) -> dict:
    out = {k: row.get(k) for k in (
        "id","product_id","robot_id","warehouse_id","current_zone",
        "current_row","current_shelf","name","category","article",
        "stock","min_stock","optimal_stock","status"
    )}
    ca = row.get("created_at")
    if ca is not None:
        out["scanned_at"] = ca if isinstance(ca, str) else ca.isoformat()
    return out


def _last_scans_key(wid: str) -> str:
    return f"wh:{wid}:lastscans"


async def _read_last_scans_from_redis(warehouse_id: str, limit: int) -> List[dict]:
    try:
        r = aioredis.from_url(
            REDIS_DSN, encoding="utf-8", decode_responses=True,
            health_check_interval=30, retry_on_timeout=True
        )
        raw = await r.lrange(_last_scans_key(warehouse_id), 0, max(0, limit - 1))
        await r.aclose()
    except Exception:
        raw = []
    scans: List[dict] = []
    for s in raw:
        try:
            scans.append(json.loads(s))
        except Exception:
            pass
    return scans[:limit]


async def _read_last_scans_from_repo(repo: InventoryHistoryRepoProto, warehouse_id: str, limit: int) -> List[dict]:
    rows = await repo.get_last_scans(warehouse_id, limit)
    out: List[dict] = []
    for ih in rows:
        payload_row = {
            "id": getattr(ih, "id", None),
            "product_id": getattr(ih, "product_id", None),
            "robot_id": getattr(ih, "robot_id", None),
            "warehouse_id": getattr(ih, "warehouse_id", None),
            "current_zone": getattr(ih, "current_zone", None),
            "current_row": getattr(ih, "current_row", None),
            "current_shelf": getattr(ih, "current_shelf", None),
            "name": getattr(ih, "name", None),
            "category": getattr(ih, "category", None),
            "article": getattr(ih, "article", None) or "unknown",
            "stock": getattr(ih, "stock", None),
            "min_stock": getattr(ih, "min_stock", None),
            "optimal_stock": getattr(ih, "optimal_stock", None),
            "status": getattr(ih, "status", None),
            "created_at": getattr(ih, "created_at", None),
        }
        out.append(_ih_row_to_payload(payload_row))
    return out


async def fetch_last_scans_snapshot(repo: InventoryHistoryRepoProto, warehouse_id: str) -> List[dict]:
    scans = await _read_last_scans_from_redis(warehouse_id, LAST_SCANS_LIMIT)
    if scans:
        return scans
    return await _read_last_scans_from_repo(repo, warehouse_id, LAST_SCANS_LIMIT)

#Публикует адресный (только для данной WS-сессии) начальный product.scan через Pub/Sub.
async def publish_initial_product_scan_unicast(repo: InventoryHistoryRepoProto, warehouse_id: str, session_id: str) -> None:
    scans = await fetch_last_scans_snapshot(repo, warehouse_id)
    payload: Dict[str, Any] = {
        "type": "product.scan",
        "warehouse_id": warehouse_id,
        "robot_id": None,                    # init-снимок
        "scans": scans,                      # newest-first
        "reason": "ws_connect_init",
        "unicast_session_id": session_id,    
        "ts": _now_iso(),
    }
    bus = await get_bus_for_current_loop()
    await bus.publish(COMMON_CH, payload)
