# app/ws/initial_product_scan_publisher.py
from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.protos import InventoryHistoryRepositoryProto
from app.repositories.bundle import inventory_history_repo_provider

logger = logging.getLogger(__name__)

LAST_SCANS_LIMIT = max(1, int(os.getenv("LAST_SCANS_LIMIT", "20")))
REDIS_DSN = os.getenv("REDIS_DSN", "redis://myapp-redis:6379/0")

try:
    import redis.asyncio as aioredis  # redis>=4.2
except Exception:  # pragma: no cover
    import aioredis  # type: ignore


# --- Локальный протокол — только то, что реально нужно этому модулю -----------
class InventoryHistoryLastScansRepoProto(Protocol):
    async def get_last_scans(self, warehouse_id: str, limit: int) -> List[Any]: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...


# Тип для читаемости: фактическая реализация проходит по duck typing
RepoForLastScans = InventoryHistoryRepositoryProto


def default_inventory_history_repo_provider() -> AsyncContextManager[RepoForLastScans]:
    """
    Провайдер на базе твоего inventory_history_repo_provider.
    commit_on_exit=False — читаем в одной транзакции и не коммитим.
    """
    return inventory_history_repo_provider(commit_on_exit=False)


# --- Вспомогательные утилиты ---------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ih_row_to_payload(row: dict) -> dict:
    """
    Нормализуем строку истории инвентаризации в компактный payload для фронта.
    created_at -> scanned_at (ISO 8601), article fallback = "unknown".
    """
    out = {k: row.get(k) for k in (
        "id", "product_id", "robot_id", "warehouse_id", "current_zone",
        "current_row", "current_shelf", "name", "category", "article",
        "stock", "min_stock", "optimal_stock", "status"
    )}
    if not out.get("article"):
        out["article"] = "unknown"

    ca = row.get("created_at")
    if ca is not None:
        out["scanned_at"] = ca if isinstance(ca, str) else ca.isoformat()
    return out


def _last_scans_key(wid: str) -> str:
    return f"wh:{wid}:lastscans"


# --- Чтение из Redis с фолбэком в репозиторий ---------------------------------
async def _read_last_scans_from_redis(warehouse_id: str, limit: int) -> List[dict]:
    client = None
    try:
        client = aioredis.from_url(
            REDIS_DSN,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
            retry_on_timeout=True,
        )
        raw = await client.lrange(_last_scans_key(warehouse_id), 0, max(0, limit - 1))
    except Exception:  # pragma: no cover
        logger.exception("Redis read error for warehouse_id=%s", warehouse_id)
        raw = []
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # pragma: no cover
                pass

    scans: List[dict] = []
    for s in raw:
        try:
            scans.append(json.loads(s))
        except Exception:  # pragma: no cover
            # Пропускаем битые записи
            continue
    return scans[:limit]


async def _read_last_scans_from_repo(
    repo: InventoryHistoryLastScansRepoProto, warehouse_id: str, limit: int
) -> List[dict]:
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


async def fetch_last_scans_snapshot(
    repo: InventoryHistoryLastScansRepoProto, warehouse_id: str
) -> List[dict]:
    # Быстрая попытка из Redis; если пусто — читаем из БД.
    scans = await _read_last_scans_from_redis(warehouse_id, LAST_SCANS_LIMIT)
    if scans:
        return scans
    return await _read_last_scans_from_repo(repo, warehouse_id, LAST_SCANS_LIMIT)


# --- Публикация и удобные вызовы ----------------------------------------------
async def publish_initial_product_scan_unicast(
    repo: InventoryHistoryLastScansRepoProto, warehouse_id: str, session_id: str
) -> None:
    """
    Публикует адресный (только для данной WS-сессии) начальный снимок product.scan через Pub/Sub.
    """
    scans = await fetch_last_scans_snapshot(repo, warehouse_id)
    payload: Dict[str, Any] = {
        "type": "product.scan",
        "warehouse_id": warehouse_id,
        "robot_id": None,            # init-снимок
        "scans": scans,              # newest-first
        "reason": "ws_connect_init",
        "unicast_session_id": session_id,
        "ts": _now_iso(),
    }
    try:
        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, payload)
    except Exception:  # pragma: no cover
        logger.exception("Publish initial product.scan failed for warehouse_id=%s", warehouse_id)


async def publish_initial_product_scan_unicast_with_provider(
    repo_provider: Callable[[], AsyncContextManager[RepoForLastScans]] = default_inventory_history_repo_provider,
    *,
    warehouse_id: str,
    session_id: str,
) -> None:
    """
    Удобный helper: откроет репозиторий через провайдер и вызовет publish_initial_product_scan_unicast.
    """
    async with repo_provider() as repo:  # commit_on_exit=False, только чтение
        await publish_initial_product_scan_unicast(repo, warehouse_id, session_id)
