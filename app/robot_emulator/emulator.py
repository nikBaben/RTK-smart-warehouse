from __future__ import annotations

# =========================
# 0) Boot flags (segfault hardening) — set BEFORE any sqlalchemy/greenlet import
# =========================
import os as _os
_os.environ.setdefault("DISABLE_CEXTENSIONS", "1")
_os.environ.setdefault("GREENLET_USE_GC", "0")
EMIT_AUTOSEND_INIT = _os.environ.setdefault("EMIT_AUTOSEND_INIT", "1") == "1"

# =========================
# 1) Stdlib & typing
# =========================
import sys
import pkgutil
import asyncio
import os
import json
import random
import multiprocessing as mp
import signal
from uuid import uuid4
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from collections import deque

# =========================
# 2) DB & ORM
# =========================
from sqlalchemy import func, insert, select, update, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import load_only

from app.db.session import async_session as AppSession
from app.core.config import settings  # noqa: F401
from app.models.warehouse import Warehouse
from app.models.robot_history import RobotHistory
from app.models.robot import Robot
from app.models.product import Product
from app.models.inventory_history import InventoryHistory

# =========================
# 3) Redis (async)
# =========================
try:
    from redis import asyncio as aioredis
except Exception:  # redis optional
    aioredis = None  # type: ignore

# =========================
# 4) Event bus
# =========================
from app.events.bus import (
    get_bus_for_current_loop,
    close_bus_for_current_loop,
    ROBOT_CH,
    COMMON_CH,
)

# =========================
# 5) Config flags
# =========================
USE_REDIS_COORD = os.getenv("USE_REDIS_COORD", "1") == "1"   # единый robot.positions координацией
USE_REDIS_CLAIMS = os.getenv("USE_REDIS_CLAIMS", "1") == "1" # глобальная бронь ячеек
REDIS_URL = os.getenv("REDIS_URL", "redis://myapp-redis:6379/0")
CLAIM_TTL_MS = int(os.getenv("CLAIM_TTL_MS", "120000"))
COORDINATOR_SHARD_INDEX = int(os.getenv("COORDINATOR_SHARD_INDEX", "0"))

# =========================
# 6) Simulation constants
# =========================
FIELD_X = 26
FIELD_Y = 50
DOCK_X, DOCK_Y = 0, 0

TICK_INTERVAL = float(os.getenv("ROBOT_TICK_INTERVAL", "0.5"))
SCAN_DURATION = timedelta(seconds=int(os.getenv("SCAN_DURATION_SEC", "6")))
RESCAN_COOLDOWN = timedelta(seconds=int(os.getenv("RESCAN_COOLDOWN_SEC", "600")))
CHARGE_DURATION = timedelta(seconds=int(os.getenv("CHARGE_DURATION_SEC", "45")))
LOW_BATTERY_THRESHOLD = float(os.getenv("LOW_BATTERY_THRESHOLD", "15"))

BATTERY_DROP_PER_STEP = float(os.getenv("BATTERY_DROP_PER_STEP", "0.6"))
POSITION_RATE_LIMIT_PER_ROBOT = float(os.getenv("POSITION_RATE_LIMIT_SEC", "0.25"))
ROBOTS_CONCURRENCY = int(os.getenv("ROBOT_CONCURRENCY", "12"))
# Сколько процентов батареи списывать за 1 секунду сканирования
SCAN_BATTERY_DROP_PER_SEC = float(os.getenv("SCAN_BATTERY_DROP_PER_SEC", "0.08"))

POSITIONS_MIN_INTERVAL_MS = int(os.getenv("POSITIONS_MIN_INTERVAL_MS", "75"))
POSITIONS_KEEPALIVE_MS = int(os.getenv("POSITIONS_KEEPALIVE_MS", "1000"))
KEEPALIVE_FULL = os.getenv("KEEPALIVE_FULL", "1") == "1"
POSITIONS_DIFFS = os.getenv("POSITIONS_DIFFS", "0") == "1"
# FIX: правильная логика включения отправки позиций (оставлено как было в твоём файле)
SEND_ROBOT_POSITION = os.getenv("SEND_ROBOT_POSITION", "1") == "0"

IDLE_GOAL_LOOKUP_EVERY = int(os.getenv("IDLE_GOAL_LOOKUP_EVERY", "2"))
ROBOTS_PER_TICK = int(os.getenv("ROBOTS_PER_TICK", "1024"))

FAST_SCAN_LOOP = os.getenv("FAST_SCAN_LOOP", "1") == "1"
FAST_SCAN_INTERVAL_MS = int(os.getenv("FAST_SCAN_INTERVAL_MS", "75"))

SCAN_MAX_DURATION_MS = int(os.getenv(
    "SCAN_MAX_DURATION_MS",
    str(int(max(1.0, SCAN_DURATION.total_seconds()) * 3000))
))

POSITIONS_BROADCAST_INTERVAL_MS = int(os.getenv("POSITIONS_BROADCAST_INTERVAL_MS", "1000"))
POSITIONS_MAX_INTERVAL_MS = int(os.getenv("POSITIONS_MAX_INTERVAL_MS", "2000"))

LAST_SCANS_LIMIT = int(os.getenv("LAST_SCANS_LIMIT", "20"))

# Настраиваемое окно выбора «самых старых» кандидатов (раньше было K=12)
STALE_PICK_TOPK = int(os.getenv("STALE_PICK_TOPK", "12"))

# ─── Multi-dock support ─────────────────────────────────────────────────────────
# Можно задать через env: DOCKS_JSON='[[0,0],[13,25]]'
try:
    _DOCKS_ENV = os.getenv("DOCKS_JSON")
    DOCKS: List[Tuple[int, int]] = [tuple(map(int, xy)) for xy in (json.loads(_DOCKS_ENV) if _DOCKS_ENV else [])]
except Exception:
    DOCKS = []

# По умолчанию — только старый док, чтобы поведение не менялось без env
if not DOCKS:
    DOCKS = [(DOCK_X, DOCK_Y)]

def nearest_dock(p: Tuple[int, int]) -> Tuple[int, int]:
    """Ближайшая док-станция до точки p (Манхэттен)."""
    return min(DOCKS, key=lambda d: abs(p[0]-d[0]) + abs(p[1]-d[1]))

def is_at_any_dock(p: Tuple[int, int]) -> bool:
    return p in DOCKS
# ────────────────────────────────────────────────────────────────────────────────

# =========================
# 7) Small hot-path constants
# =========================
ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH_IDX = {c: i + 1 for i, c in enumerate(ALPH)}
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_BILLION = 10 ** 9

# =========================
# 8) Redis helpers
# =========================
_redis_pool = None

def _r_key_lastscans(wid: str) -> str:
    return f"wh:{wid}:lastscans"

def _r_key_claim(wid: str, x: int, y: int) -> str:
    return f"wh:{wid}:claim:{x}:{y}"

def _r_key_robots_hash(wid: str) -> str:
    return f"wh:{wid}:robots"

def _r_key_robots_ver(wid: str) -> str:
    return f"wh:{wid}:robots:ver"

def _r_key_robots_lastmap(wid: str) -> str:
    return f"wh:{wid}:robots:lastsent"

def _r_key_stale_zset(wid: str) -> str:
    # ZSET: member="x:y", score = Unix ts of min(last_scanned_at). Чем меньше — тем старее.
    return f"wh:{wid}:stale:z"

async def _get_redis():
    global _redis_pool
    if not (USE_REDIS_COORD or USE_REDIS_CLAIMS):
        return None
    if aioredis is None:
        raise RuntimeError("redis[async] не установлен, а USE_REDIS_* = 1")
    if _redis_pool is None:
        _redis_pool = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis_pool

async def _close_redis():
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.close()
        except Exception:
            pass
        _redis_pool = None

# =========================
# 9) Local process memory / caches
# =========================
_TARGETS: Dict[str, Tuple[int, int]] = {}
_SCANNING_UNTIL: Dict[str, datetime] = {}
_SCANNING_CELL: Dict[str, Tuple[int, int]] = {}
_SCANNING_STARTED_AT: Dict[str, datetime] = {}
_LAST_POS_SENT_AT: Dict[str, datetime] = {}
_CLAIMED: Dict[str, Set[Tuple[int, int]]] = {}

_WH_SNAPSHOT: Dict[str, Dict[str, dict]] = {}
_WH_SNAPSHOT_VER: Dict[str, int] = {}
_WH_LAST_SENT_VER: Dict[str, int] = {}
_WH_LAST_SENT_MAP: Dict[str, Dict[str, dict]] = {}
_LAST_POS_BROADCAST_AT: Dict[str, float] = {}
_LAST_ANY_SENT_AT: Dict[str, float] = {}
_WH_LOCKS: Dict[str, asyncio.Lock] = {}

_ELIGIBLE_CACHE: Dict[str, dict] = {}
_WH_TICK_COUNTER: Dict[str, int] = {}

_ROBOT_WH: Dict[str, str] = {}
_WH_ROBOT_OFFSET: Dict[str, int] = {}

_WH_FASTSCAN_TASK: Dict[str, asyncio.Task] = {}
_WH_POS_TASK: Dict[str, asyncio.Task] = {}

_SCANNING_FINISHING: Dict[str, bool] = {}
_SCAN_LOCKS: Dict[str, asyncio.Lock] = {}

_LAST_SCANS_CACHE: Dict[str, deque] = {}

# Во время сканирования: отметка последнего списания батареи
_SCANNING_BATT_LAST_AT: Dict[str, datetime] = {}

# ===== Shard
_SHARD_IDX = 0
_SHARD_COUNT = 1

# =========================
# 10) Utils (hot path friendly)
# =========================
def _scan_lock(rid: str) -> asyncio.Lock:
    lk = _SCAN_LOCKS.get(rid)
    if lk is None:
        lk = _SCAN_LOCKS[rid] = asyncio.Lock()
    return lk

def _wh_lock(wid: str) -> asyncio.Lock:
    lk = _WH_LOCKS.get(wid)
    if lk is None:
        lk = asyncio.Lock()
        _WH_LOCKS[wid] = lk
    return lk

def _claimed_set(wid: str) -> Set[Tuple[int, int]]:
    return _CLAIMED.setdefault(wid, set())

def _claim_local(wid: str, cell: Tuple[int, int]) -> None:
    _claimed_set(wid).add(cell)

def _free_claim_local(wid: str, cell: Tuple[int, int]) -> None:
    _claimed_set(wid).discard(cell)

def _wh_snapshot(wid: str) -> Dict[str, dict]:
    return _WH_SNAPSHOT.setdefault(wid, {})

def _last_sent_map(wid: str) -> Dict[str, dict]:
    return _WH_LAST_SENT_MAP.setdefault(wid, {})

def _last_scans_deque(wid: str) -> deque:
    dq = _LAST_SCANS_CACHE.get(wid)
    if dq is None or dq.maxlen != LAST_SCANS_LIMIT:
        dq = _LAST_SCANS_CACHE[wid] = deque(maxlen=LAST_SCANS_LIMIT)
    return dq

def shelf_num_to_str(n: int) -> str:
    return ALPH[max(0, min(25, n - 1))] if n > 0 else "0"

def shelf_str_to_num(s: Optional[str]) -> int:
    if not s:
        return 0
    s = s.strip().upper()
    if not s or s == "0":
        return 0
    return ALPH_IDX.get(s[0], 0)

def clamp_xy(x: int, y: int) -> Tuple[int, int]:
    if x < 0: x = 0
    elif x > FIELD_X: x = FIELD_X
    if y < 0: y = 0
    elif y >= FIELD_Y: y = FIELD_Y - 1
    return x, y

def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def robot_xy(robot: Robot) -> Tuple[int, int]:
    return int(robot.current_shelf or 0), int(robot.current_row or 0)

def set_robot_xy(robot: Robot, x: int, y: int) -> None:
    robot.current_shelf = int(x or 0)
    robot.current_row = int(y or 0)

def _set_shard(idx: int, count: int) -> None:
    global _SHARD_IDX, _SHARD_COUNT
    _SHARD_IDX, _SHARD_COUNT = idx, max(1, count)

# =========================
# 11) Status logging & set_status (debounced)
# =========================
LAST_STATUS_CACHE: Dict[str, Tuple[str, datetime]] = {}

async def _log_robot_status(session: AsyncSession, robot: Robot, status: str) -> None:
    try:
        await session.execute(
            insert(RobotHistory).values(
                id=str(uuid4()),
                robot_id=robot.id,
                warehouse_id=robot.warehouse_id,
                status=status,
                created_at=datetime.now(timezone.utc),
            )
        )
    except Exception as e:
        print(f"⚠️ robot status log failed rid={robot.id} status={status}: {e}", flush=True)

async def set_status(
    session: AsyncSession,
    robot: Robot,
    new_status: str,
    *,
    dedupe_seconds: int = 2,
    force_log: bool = False,
) -> None:
    new_status = (new_status or "").lower()
    cur = (robot.status or "").lower()
    now = datetime.now(timezone.utc)

    if force_log:
        robot.status = new_status
        await session.flush()
        try:
            await session.execute(
                insert(RobotHistory).values(
                    id=str(uuid4()),
                    robot_id=robot.id,
                    warehouse_id=robot.warehouse_id,
                    status=new_status,
                    created_at=now,
                )
            )
        except Exception as e:
            print(f"⚠️ robot status force-log failed rid={robot.id} status={new_status}: {e}", flush=True)
        _update_wh_snapshot_from_robot(robot)
        LAST_STATUS_CACHE[robot.id] = (new_status, now)
        return

    if cur == new_status:
        await session.flush()
        _update_wh_snapshot_from_robot(robot)
        return

    last = LAST_STATUS_CACHE.get(robot.id)
    if last and last[0] == new_status and (now - last[1]).total_seconds() < dedupe_seconds:
        robot.status = new_status
        await session.flush()
        _update_wh_snapshot_from_robot(robot)
        return

    robot.status = new_status
    await session.flush()
    await _log_robot_status(session, robot, new_status)
    _update_wh_snapshot_from_robot(robot)
    LAST_STATUS_CACHE[robot.id] = (new_status, now)

# =========================
# 12) Emitting events
# =========================
async def _emit(evt: dict) -> None:
    t = evt.get("type", "")
    ch = ROBOT_CH if t.startswith("robot.position") or t in {
        "robot.positions", "robot.positions.diff", "robot.positions.keepalive", "product.scan"
    } else COMMON_CH
    bus = await get_bus_for_current_loop()
    await bus.publish(ch, evt)

async def _emit_position_if_needed(robot: Robot) -> None:
    if not SEND_ROBOT_POSITION:
        return
    now = datetime.now(timezone.utc)
    last = _LAST_POS_SENT_AT.get(robot.id)
    if last and (now - last).total_seconds() < POSITION_RATE_LIMIT_PER_ROBOT:
        return
    _LAST_POS_SENT_AT[robot.id] = now
    x, y = robot_xy(robot)
    await _emit({
        "type": "robot.position",
        "warehouse_id": robot.warehouse_id,
        "robot_id": robot.id,
        "x": x,
        "y": y,
        "shelf": shelf_num_to_str(x),
        "battery_level": round(float(robot.battery_level or 0.0), 1),
        "status": (robot.status or "idle"),
        "ts": now.isoformat(),
    })

# =========================
# 13) Snapshot helpers (robots positions)
# =========================
async def _write_robot_to_redis(robot: Robot, item: dict) -> None:
    if not USE_REDIS_COORD:
        return
    r = await _get_redis()
    await r.hset(_r_key_robots_hash(robot.warehouse_id), robot.id, json.dumps(item))

def _update_wh_snapshot_from_robot(robot: Robot) -> None:
    wid = robot.warehouse_id
    _ROBOT_WH[robot.id] = wid
    x_int, y_int = robot_xy(robot)
    now_iso = datetime.now(timezone.utc).isoformat()

    base = {
        "robot_id": robot.id,
        "x": x_int,
        "y": y_int,
        "shelf": shelf_num_to_str(x_int),
        "battery_level": round(float(robot.battery_level or 0.0), 1),
        "status": (robot.status or "idle"),
    }

    snap = _wh_snapshot(wid)
    old_item = snap.get(robot.id) or {}
    changed = {k: old_item.get(k) for k in base.keys()} != base
    updated_at = now_iso if changed else (old_item.get("updated_at") or now_iso)
    new_item = dict(base, updated_at=updated_at)

    if old_item != new_item:
        snap[robot.id] = new_item
        _WH_SNAPSHOT_VER[wid] = _WH_SNAPSHOT_VER.get(wid, 0) + 1
        if USE_REDIS_COORD:
            asyncio.create_task(_write_robot_to_redis(robot, new_item))

def _is_scanning_in_snapshot(wid: str, rid: str) -> bool:
    item = _wh_snapshot(wid).get(rid)
    return bool(item and (item.get("status") or "").lower() == "scanning")

def _calc_diff_payload(wid: str, snap: Dict[str, dict]) -> Tuple[List[dict], List[str]]:
    last = _last_sent_map(wid)
    changed: List[dict] = []
    removed: List[str] = []
    for rid, item in snap.items():
        if last.get(rid) != item:
            changed.append(item)
    for rid in list(last.keys()):
        if rid not in snap:
            removed.append(rid)
    return changed, removed

def _remember_last_sent_map(wid: str, snap: Dict[str, dict]) -> None:
    _WH_LAST_SENT_MAP[wid] = {rid: dict(item) for rid, item in snap.items()}

# =========================
# 14) Products: last scans cache emit (fast)
# =========================
def _ih_row_to_payload(row: dict) -> dict:
    out = {
        "id": row["id"],
        "product_id": row["product_id"],
        "robot_id": row["robot_id"],
        "warehouse_id": row["warehouse_id"],
        "current_zone": row.get("current_zone"),
        "current_row": row.get("current_row"),
        "current_shelf": row.get("current_shelf"),
        "name": row.get("name"),
        "category": row.get("category"),
        "article": row.get("article"),
        "stock": row.get("stock"),
        "min_stock": row.get("min_stock"),
        "optimal_stock": row.get("optimal_stock"),
        "status": row.get("status"),
    }
    ca = row.get("created_at")
    if ca is not None:
        out["scanned_at"] = ca if isinstance(ca, str) else ca.isoformat()
    return out

async def _append_last_scans(wid: str, items: List[dict]) -> None:
    if not items:
        return
    dq = _last_scans_deque(wid)
    for it in items:
        dq.append(it)
    if USE_REDIS_COORD or USE_REDIS_CLAIMS:
        try:
            r = await _get_redis()
            if r is not None:
                key = _r_key_lastscans(wid)
                pipe = r.pipeline()
                for it in reversed(items):  # новые в голову
                    pipe.lpush(key, json.dumps(it, ensure_ascii=False))
                pipe.ltrim(key, 0, LAST_SCANS_LIMIT - 1)
                await pipe.execute()
        except Exception:
            pass

async def _get_last_scans(wid: str, session: Optional[AsyncSession] = None) -> List[dict]:
    if USE_REDIS_COORD or USE_REDIS_CLAIMS:
        try:
            r = await _get_redis()
            if r is not None:
                raw = await r.lrange(_r_key_lastscans(wid), 0, LAST_SCANS_LIMIT - 1)
                scans = []
                for s in raw:
                    try:
                        scans.append(json.loads(s))
                    except Exception:
                        pass
                if scans:
                    dq = _last_scans_deque(wid)
                    dq.clear()
                    for it in reversed(scans):
                        dq.append(it)
                    return scans
        except Exception:
            pass
    dq = _last_scans_deque(wid)
    if dq:
        return list(dq)[-LAST_SCANS_LIMIT:][::-1]

    if session is not None:
        try:
            try:
                res = await session.execute(
                    select(InventoryHistory)
                    .where(InventoryHistory.warehouse_id == wid)
                    .order_by(InventoryHistory.created_at.desc())
                    .limit(LAST_SCANS_LIMIT)
                )
            except Exception:
                res = await session.execute(
                    select(InventoryHistory)
                    .where(InventoryHistory.warehouse_id == wid)
                    .order_by(InventoryHistory.id.desc())
                    .limit(LAST_SCANS_LIMIT)
                )
            rows = res.scalars().all()
            scans = []
            for ih in rows:
                scans.append(_ih_row_to_payload({
                    "id": ih.id,
                    "product_id": ih.product_id,
                    "robot_id": ih.robot_id,
                    "warehouse_id": ih.warehouse_id,
                    "current_zone": ih.current_zone,
                    "current_row": ih.current_row,
                    "current_shelf": ih.current_shelf,
                    "name": ih.name,
                    "category": ih.category,
                    "article": ih.article,
                    "stock": ih.stock,
                    "min_stock": ih.min_stock,
                    "optimal_stock": ih.optimal_stock,
                    "status": ih.status,
                    **({"created_at": getattr(ih, "created_at")} if hasattr(ih, "created_at") else {}),
                }))
            await _append_last_scans(wid, list(reversed(scans)))
            return scans
        except Exception:
            pass
    return []

async def _emit_last_scans(
    session: AsyncSession,
    warehouse_id: str,
    robot_id: Optional[str],
    reason: Optional[str] = None,
    scans_override: Optional[List[dict]] = None,
) -> None:
    scans = scans_override if scans_override is not None else await _get_last_scans(warehouse_id, session=session)
    payload = {
        "type": "product.scan",
        "warehouse_id": warehouse_id,
        "robot_id": robot_id,
        "scans": scans,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if reason:
        payload["reason"] = reason
    await _emit(payload)

async def _emit_product_scans_init(warehouse_id: str) -> None:
    async with AppSession() as s:
        async with s.begin():
            await _emit_last_scans(s, warehouse_id, robot_id=None, reason="autosend_init")

# =========================
# 14a) Battery drain helpers (scan)
# =========================
def _drain_scan_battery(robot: Robot, now: datetime) -> bool:
    """
    Уменьшает батарею во время сканирования пропорционально прошедшему времени.
    Возвращает True, если заряд действительно изменился.
    """
    rid = robot.id
    last = _SCANNING_BATT_LAST_AT.get(rid)
    if last is None:
        _SCANNING_BATT_LAST_AT[rid] = now
        return False
    dt = (now - last).total_seconds()
    if dt <= 0:
        return False
    drop = SCAN_BATTERY_DROP_PER_SEC * dt
    cur = float(robot.battery_level or 0.0)
    new = max(0.0, cur - drop)
    if new == cur:
        _SCANNING_BATT_LAST_AT[rid] = now
        return False
    robot.battery_level = new
    _SCANNING_BATT_LAST_AT[rid] = now
    return True

# =========================
# 15) Redis claims (global)
# =========================
async def _claim_global(wid: str, cell: Tuple[int, int]) -> bool:
    if not USE_REDIS_CLAIMS:
        return True
    r = await _get_redis()
    if r is None:
        return True
    x, y = cell
    ok = await r.set(_r_key_claim(wid, x, y), "1", nx=True, px=CLAIM_TTL_MS)
    return bool(ok)

async def _renew_claim_global(wid: str, cell: Tuple[int, int]) -> None:
    """Продление TTL брони клетки, пока робот к ней едет."""
    if not USE_REDIS_CLAIMS:
        return
    r = await _get_redis()
    if r is None:
        return
    x, y = cell
    key = _r_key_claim(wid, x, y)
    try:
        await r.pexpire(key, CLAIM_TTL_MS)
    except Exception:
        pass

async def _free_claim_global(wid: str, cell: Tuple[int, int]) -> None:
    x, y = cell
    if not USE_REDIS_CLAIMS:
        _free_claim_local(wid, cell)
        return
    try:
        r = await _get_redis()
        if r is not None:
            await r.delete(_r_key_claim(wid, x, y))
    finally:
        _free_claim_local(wid, cell)

# =========================
# 16) Eligibility / staleness sources (FAST)
# =========================
async def _seed_staleness_zset(session: AsyncSession, wid: str) -> None:
    """
    Инициализируем ZSET (по складу) значениями min(last_scanned_at) по клеткам.
    Делаем это один раз при прогреве — дальше обновляем инкрементально.
    """
    if aioredis is None:
        return
    r = await _get_redis()
    zkey = _r_key_stale_zset(wid)

    # Берём агрегат одной SQL
    rows = await session.execute(
        select(
            Product.current_row.label("row"),
            func.upper(func.trim(Product.current_shelf)).label("shelf"),
            func.min(func.coalesce(Product.last_scanned_at, EPOCH)).label("min_scan_at"),
        )
        .where(Product.warehouse_id == wid, func.upper(func.trim(Product.current_shelf)) != "0")
        .group_by(Product.current_row, func.upper(func.trim(Product.current_shelf)))
    )

    pipe = r.pipeline()
    pipe.delete(zkey)
    # batched ZADD
    cnt = 0
    for row, shelf_str, min_scan_at in rows.all():
        x = shelf_str_to_num(shelf_str)
        y = int(row or 0)
        if 1 <= x <= FIELD_X and 0 <= y <= FIELD_Y - 1:
            ts = (min_scan_at or EPOCH).timestamp()
            pipe.zadd(zkey, {f"{x}:{y}": ts})
            cnt += 1
            if (cnt % 512) == 0:
                await pipe.execute()
                pipe = r.pipeline()
    await pipe.execute()

async def _update_staleness_cell(wid: str, x: int, y: int, ts: float) -> None:
    """После скана клетки обновляем её «возраст» в ZSET (быстро, O(log N))."""
    if aioredis is None:
        return
    r = await _get_redis()
    await r.zadd(_r_key_stale_zset(wid), {f"{x}:{y}": ts})

async def _zrange_oldest_cells(wid: str, limit: int = 256) -> List[Tuple[int, int, float]]:
    """Берём из Redis ZSET самые «старые» клетки (минимальный score)."""
    if aioredis is None:
        return []
    r = await _get_redis()
    zkey = _r_key_stale_zset(wid)
    # ZRANGE ... WITHSCORES (decode_responses=True)
    data = await r.zrange(zkey, 0, max(0, limit - 1), withscores=True)
    out: List[Tuple[int, int, float]] = []
    for member, score in data:
        try:
            x_str, y_str = member.split(":", 1)
            x, y = int(x_str), int(y_str)
            if 1 <= x <= FIELD_X and 0 <= y < FIELD_Y:
                out.append((x, y, float(score)))
        except Exception:
            continue
    return out

async def _filter_cells_eligible(
    session: AsyncSession, wid: str, cells: List[Tuple[int, int]], cutoff: datetime
) -> List[Tuple[int, int]]:
    """
    Быстрый фильтр «есть ли в клетке eligible-товары» одной SQL.
    Ограничиваем список до разумного размера (на входе уже «старые»).
    """
    if not cells:
        return []
    # Преобразуем в (row, shelf_str)
    rs_pairs: List[Tuple[int, str]] = []
    for (x, y) in cells:
        rs_pairs.append((y, shelf_num_to_str(x)))
    # tuple_ (row, shelf) IN (...)
    res = await session.execute(
        select(Product.current_row, func.upper(func.trim(Product.current_shelf)))
        .where(
            Product.warehouse_id == wid,
            tuple_(Product.current_row, func.upper(func.trim(Product.current_shelf))).in_(rs_pairs),
            (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
        )
        .distinct()
    )
    eligible_set: Set[Tuple[int, str]] = set((int(r), s) for r, s in res.all())
    out: List[Tuple[int, int]] = []
    for (x, y) in cells:
        if (y, shelf_num_to_str(x)) in eligible_set:
            out.append((x, y))
    return out

# legacy (fallback) — полный обход (редко, при пустом ZSET), теперь с ORDER BY min(last_scanned_at)
async def _eligible_cells(session: AsyncSession, wid: str, cutoff: datetime) -> List[Tuple[int, int]]:
    rows = await session.execute(
        select(
            Product.current_row,
            func.upper(func.trim(Product.current_shelf)).label("shelf"),
            func.min(func.coalesce(Product.last_scanned_at, EPOCH)).label("min_scan")
        )
        .where(
            Product.warehouse_id == wid,
            func.upper(func.trim(Product.current_shelf)) != "0",
            (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
        )
        .group_by(Product.current_row, func.upper(func.trim(Product.current_shelf)))
        .order_by(func.min(func.coalesce(Product.last_scanned_at, EPOCH)).asc())
    )
    out: List[Tuple[int, int]] = []
    for y_int, shelf_str, _min_scan in rows.all():
        x = shelf_str_to_num(shelf_str)
        y = int(y_int or 0)
        if 1 <= x <= FIELD_X and 0 <= y < FIELD_Y:
            out.append((x, y))
    return out

async def _eligible_products_in_cell(
    session: AsyncSession, wid: str, x: int, y: int, cutoff: datetime
) -> List[Product]:
    shelf = shelf_num_to_str(x)
    res = await session.execute(
        select(Product)
        .options(
            load_only(
                Product.id, Product.name, Product.category, Product.article,
                Product.stock, Product.min_stock, Product.optimal_stock,
                Product.current_zone, Product.current_row, Product.current_shelf,
            )
        )
        .where(
            Product.warehouse_id == wid,
            Product.current_row == y,
            func.upper(func.trim(Product.current_shelf)) == shelf,
            (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
        )
    )
    return list(res.scalars().all())

# =========================
# 17) Scanning lifecycle (optimized)
# =========================
async def _start_scan(session: AsyncSession, robot: Robot, x: int, y: int) -> None:
    await set_status(session, robot, "scanning")
    _SCANNING_CELL[robot.id] = (x, y)
    now = datetime.now(timezone.utc)
    _SCANNING_STARTED_AT[robot.id] = now
    _SCANNING_UNTIL[robot.id] = now + SCAN_DURATION
    _SCANNING_BATT_LAST_AT[robot.id] = now
    _update_wh_snapshot_from_robot(robot)

async def _finish_scan(session: AsyncSession, robot: Robot) -> None:
    rx, ry = _SCANNING_CELL.pop(robot.id, robot_xy(robot))
    _SCANNING_UNTIL.pop(robot.id, None)
    _SCANNING_STARTED_AT.pop(robot.id, None)
    _SCANNING_BATT_LAST_AT.pop(robot.id, None)

    shelf = shelf_num_to_str(rx)
    if shelf == "0":
        await _free_claim_global(robot.warehouse_id, (rx, ry))
        await set_status(session, robot, "idle")
        await _emit_last_scans(session, robot.warehouse_id, robot.id, reason="no_valid_shelf")
        return

    now_dt = datetime.now(timezone.utc)
    cutoff = now_dt - RESCAN_COOLDOWN

    products = await _eligible_products_in_cell(session, robot.warehouse_id, rx, ry, cutoff)
    if not products:
        await _free_claim_global(robot.warehouse_id, (rx, ry))
        await set_status(session, robot, "idle")
        await _emit_last_scans(session, robot.warehouse_id, robot.id, reason="under_cooldown")
        # Даже если «нечего сканить», мы обновляем «давность» на текущий момент — чтобы клетка не болталась в топе.
        await _update_staleness_cell(robot.warehouse_id, rx, ry, now_dt.timestamp())
        return

    now_iso = now_dt.isoformat()
    rows_payload: List[dict] = []
    payload_for_cache: List[dict] = []
    ids_update: List[str] = []

    # Минимизируем Python-работу в цикле
    for p in products:
        stock = int(p.stock or 0)
        if p.min_stock is not None and stock < p.min_stock:
            status = "critical"
        elif p.optimal_stock is not None and stock < p.optimal_stock:
            status = "low"
        else:
            status = "ok"

        ih_row = {
            "id": f"ih_{os.urandom(6).hex()}",
            "product_id": p.id,
            "robot_id": robot.id,
            "warehouse_id": robot.warehouse_id,
            "current_zone": getattr(p, "current_zone", "Хранение"),
            "current_row": ry,
            "current_shelf": shelf,
            "name": p.name,
            "category": p.category,
            "article": getattr(p, "article", None) or "unknown",
            "stock": stock,
            "min_stock": p.min_stock,
            "optimal_stock": p.optimal_stock,
            "status": status,
        }
        rows_payload.append(ih_row)
        payload_for_cache.append(_ih_row_to_payload({**ih_row, "created_at": now_iso}))
        ids_update.append(p.id)

    await session.execute(insert(InventoryHistory), rows_payload)
    await session.execute(
        update(Product)
        .where(Product.id.in_(ids_update))
        .values(last_scanned_at=now_dt)
    )

    await _append_last_scans(robot.warehouse_id, payload_for_cache)
    scans20 = await _get_last_scans(robot.warehouse_id)
    await _emit_last_scans(session, robot.warehouse_id, robot.id, scans_override=scans20)

    # ✨ ОБНОВЛЯЕМ ZSET «давности» — одна операция
    await _update_staleness_cell(robot.warehouse_id, rx, ry, now_dt.timestamp())

    await _free_claim_global(robot.warehouse_id, (rx, ry))
    await set_status(session, robot, "idle")

async def _safe_finish_scan(session: AsyncSession, robot: Robot) -> None:
    async with _scan_lock(robot.id):
        if _SCANNING_FINISHING.get(robot.id):
            return
        if (robot.id not in _SCANNING_UNTIL) and (robot.status or "").lower() != "scanning":
            return
        _SCANNING_FINISHING[robot.id] = True
    try:
        await _finish_scan(session, robot)
    except Exception as e:
        rx, ry = robot_xy(robot)
        _SCANNING_CELL.pop(robot.id, None)
        _SCANNING_UNTIL.pop(robot.id, None)
        _SCANNING_STARTED_AT.pop(robot.id, None)
        _SCANNING_BATT_LAST_AT.pop(robot.id, None)
        await _free_claim_global(robot.warehouse_id, (rx, ry))
        await set_status(session, robot, "idle")
        try:
            await _emit_last_scans(session, robot.warehouse_id, robot.id, reason="scan_error")
        except Exception:
            pass
        print(f"⚠️ safe_finish_scan: error rid={robot.id}: {e}", flush=True)
    finally:
        async with _scan_lock(robot.id):
            _SCANNING_FINISHING.pop(robot.id, None)
            _SCANNING_BATT_LAST_AT.pop(robot.id, None)

# =========================
# 18) Eligibility quick check
# =========================
async def _cell_still_eligible(session: AsyncSession, wid: str, cell: Tuple[int, int], cutoff: datetime) -> bool:
    x, y = cell
    shelf = shelf_num_to_str(x)
    row = await session.execute(
        select(Product.id).where(
            Product.warehouse_id == wid,
            Product.current_row == y,
            func.upper(func.trim(Product.current_shelf)) == shelf,
            (Product.last_scanned_at.is_(None)) | (Product.last_scanned_at < cutoff),
        ).limit(1)
    )
    return row.first() is not None

# =========================
# 19) Per-tick cache
# =========================
def _next_tick_id(wid: str) -> int:
    _WH_TICK_COUNTER[wid] = _WH_TICK_COUNTER.get(wid, 0) + 1
    return _WH_TICK_COUNTER[wid]

def _get_tick_cache(wid: str, tick_id: int) -> dict:
    c = _ELIGIBLE_CACHE.get(wid)
    if not c or c.get("tick_id") != tick_id:
        c = _ELIGIBLE_CACHE[wid] = {
            "tick_id": tick_id,
            "cutoff": None,
            "by_cell": {},
            "local_selected": set(),
            # Precomputed per tick queues (FAST):
            "goals_queue": None,     # List[Tuple[int,int]] — общий для склада пул целей на тик
            "cells": None,           # legacy fallback
        }
    return c

# =========================
# 20) Robot tick (optimized)
# =========================
async def _robot_tick(session: AsyncSession, robot_id: str, tick_id: Optional[int] = None) -> None:
    # Single small select — keep hot fields only
    rres = await session.execute(
        select(Robot)
        .options(load_only(
            Robot.id, Robot.warehouse_id, Robot.status,
            Robot.battery_level, Robot.current_row, Robot.current_shelf,
        ))
        .where(Robot.id == robot_id)
    )
    robot = rres.scalar_one_or_none()
    if not robot:
        return

    wid = robot.warehouse_id
    _ROBOT_WH[robot.id] = wid
    tid = tick_id or _next_tick_id(wid)
    cache = _get_tick_cache(wid, tid)
    now_dt = datetime.now(timezone.utc)
    cutoff = now_dt - RESCAN_COOLDOWN
    cache["cutoff"] = cutoff

    # 1) if scanning — fast path
    if (robot.status or "").lower() == "scanning":
        if robot.id not in _SCANNING_UNTIL:
            _SCANNING_STARTED_AT[robot.id] = now_dt
            _SCANNING_UNTIL[robot.id] = now_dt
            _SCANNING_CELL.setdefault(robot.id, robot_xy(robot))
        # Списываем батарею во время сканирования и обновляем снапшот,
        # чтобы robot.positions отражал текущий уровень заряда.
        if _drain_scan_battery(robot, now_dt):
            await session.flush()
            _update_wh_snapshot_from_robot(robot)
            await _maybe_emit_positions_snapshot_inmem(wid)
            await _emit_position_if_needed(robot)
        if FAST_SCAN_LOOP:
            return
        start_at = _SCANNING_STARTED_AT.get(robot.id)
        if start_at and (now_dt - start_at).total_seconds() * 1000.0 > SCAN_MAX_DURATION_MS:
            await _safe_finish_scan(session, robot)
            await session.flush()
            _update_wh_snapshot_from_robot(robot)
            await _maybe_emit_positions_snapshot_inmem(wid)
            return
        until = _SCANNING_UNTIL.get(robot.id)
        if until and now_dt >= until:
            await _safe_finish_scan(session, robot)
            await session.flush()
            _update_wh_snapshot_from_robot(robot)
            await _emit_position_if_needed(robot)
            await _maybe_emit_positions_snapshot_inmem(wid)
        return

    # 2) charging
    if (robot.status or "").lower() == "charging":
        inc = 100.0 * (TICK_INTERVAL / CHARGE_DURATION.total_seconds())
        robot.battery_level = min(100.0, float(robot.battery_level or 0.0) + inc)
        if float(robot.battery_level) >= 100.0:
            await set_status(session, robot, "idle")
        else:
            await set_status(session, robot, "charging", force_log=True)
        await _emit_position_if_needed(robot)
        await _maybe_emit_positions_snapshot_inmem(wid)
        return

    # 3) goal selection
    cur = robot_xy(robot)
    goal = _TARGETS.get(robot.id)
    low_batt = float(robot.battery_level or 0.0) <= LOW_BATTERY_THRESHOLD

    # eligibility re-check теперь только «на подлёте»
    if goal is not None and not low_batt:
        dist = manhattan(cur, goal)
        if dist <= 1:
            if not await _cell_still_eligible(session, wid, goal, cutoff):
                await _free_claim_global(wid, goal)
                _TARGETS.pop(robot.id, None)
                goal = None

    if low_batt:
        if goal:
            await _free_claim_global(wid, goal)
            _TARGETS.pop(robot.id, None)
        goal = nearest_dock(cur)  # <-- ездим на ближайший док
    else:
        if goal is None and (tid % IDLE_GOAL_LOOKUP_EVERY == 0):
            # ✨ NEW: precompute per-tick goals queue ONCE per warehouse (global shared within tick)
            if cache["goals_queue"] is None:
                # 1) Try Redis ZSET oldest cells (zero-alloc-ish)
                oldest = await _zrange_oldest_cells(wid, limit=256) or []
                # Convert to list of (x, y)
                oldest_cells = [(x, y) for (x, y, _score) in oldest]
                # Filter by cutoff in ONE SQL (cap to 64 for speed)
                if oldest_cells:
                    qcells = oldest_cells[:64]
                    eligible = await _filter_cells_eligible(session, wid, qcells, cutoff)
                else:
                    # Fallback single SQL (rare) — уже упорядочен по давности
                    eligible = await _eligible_cells(session, wid, cutoff)

                # Stable order: oldest first; tie-breaker: per robot мы предпочтем ближайшие позже.
                cache["goals_queue"] = eligible

            # Try to take the best goal from queue considering claims & distance (tie-breaker)
            if cache["goals_queue"]:
                claimed = _claimed_set(wid)
                local_sel: Set[Tuple[int, int]] = cache["local_selected"]

                # iterate few items and pick nearest among the first K (env-configurable)
                K = max(1, STALE_PICK_TOPK)
                candidates = []
                taken = 0
                for c in cache["goals_queue"]:
                    if (not USE_REDIS_CLAIMS and c in claimed) or c in local_sel:
                        continue
                    candidates.append(c)
                    taken += 1
                    if taken >= K:
                        break

                if candidates:
                    # nearest among candidates
                    best = None
                    best_d = None
                    for c in candidates:
                        d = manhattan(cur, c)
                        if best is None or d < (best_d or _BILLION):
                            best, best_d = c, d
                    if best is not None:
                        async with _wh_lock(wid):
                            cache_now = _get_tick_cache(wid, tid)
                            local_sel_now: Set[Tuple[int, int]] = cache_now["local_selected"]
                            if best not in local_sel_now:
                                if await _claim_global(wid, best):
                                    local_sel_now.add(best)
                                    if not USE_REDIS_CLAIMS:
                                        _claim_local(wid, best)
                                    _TARGETS[robot.id] = best
                                    goal = best

    # 4) Move step
    cur_x, cur_y = cur
    if goal:
        tx, ty = goal
        nx = cur_x + (1 if tx > cur_x else (-1 if tx < cur_x else 0))
        ny = cur_y if nx != tx else (cur_y + (1 if ty > cur_y else (-1 if ty < cur_y else 0)))
    else:
        # random small drift but avoid X=0
        cand = [(cur_x + 1, cur_y), (cur_x - 1, cur_y), (cur_x, cur_y + 1), (cur_x, cur_y - 1)]
        valid = [(x, y) for (x, y) in cand if 1 <= x <= FIELD_X and 0 <= y < FIELD_Y]
        if valid:
            nx, ny = random.choice(valid)
        else:
            nx, ny = (cur_x, cur_y)

    nx, ny = clamp_xy(nx, ny)
    moved = (nx, ny) != (cur_x, cur_y)
    if moved:
        robot.battery_level = max(0.0, float(robot.battery_level or 0.0) - BATTERY_DROP_PER_STEP)

    # Battery died → dock (ближайший)
    if float(robot.battery_level or 0.0) <= 0.0:
        dx, dy = nearest_dock((cur_x, cur_y))
        set_robot_xy(robot, dx, dy)
        await set_status(session, robot, "charging")
        if goal and not is_at_any_dock(goal):
            await _free_claim_global(wid, goal)
        _TARGETS.pop(robot.id, None)
        await _emit_position_if_needed(robot)
        await _maybe_emit_positions_snapshot_inmem(wid)
        return

    set_robot_xy(robot, nx, ny)
    await set_status(session, robot, "idle")
    await _emit_position_if_needed(robot)
    await _maybe_emit_positions_snapshot_inmem(wid)

    # Пока едем к цели — продлеваем бронь, чтобы её не «увели»
    if goal and (nx, ny) != goal and not low_batt:
        await _renew_claim_global(wid, goal)

    # Приехали на ДОК — начинаем зарядку
    if is_at_any_dock((nx, ny)) and float(robot.battery_level) < 100.0:
        await set_status(session, robot, "charging")
        if goal and not is_at_any_dock(goal):
            await _free_claim_global(wid, goal)
        _TARGETS.pop(robot.id, None)
        await _maybe_emit_positions_snapshot_inmem(wid)
        return

    if goal and (nx, ny) == goal:
        key = (nx, ny)
        if key not in cache["by_cell"]:
            cache["by_cell"][key] = await _eligible_products_in_cell(session, wid, nx, ny, cutoff)
        eligible_now = cache["by_cell"][key]
        if eligible_now:
            await _start_scan(session, robot, nx, ny)
        else:
            await _free_claim_global(wid, goal)
        _TARGETS.pop(robot.id, None)
        await session.flush()
        _update_wh_snapshot_from_robot(robot)
        await _maybe_emit_positions_snapshot_inmem(wid)

# =========================
# 21) Positions broadcaster (unchanged logic, minor micro-opts)
# =========================
async def _maybe_emit_positions_snapshot_inmem(wid: str) -> None:
    if USE_REDIS_COORD:
        return
    loop = asyncio.get_running_loop()
    now_mono = loop.time()
    last_any = _LAST_ANY_SENT_AT.get(wid, 0.0)
    need_keepalive = (now_mono - last_any) * 1000.0 >= POSITIONS_KEEPALIVE_MS
    last_rl = _LAST_POS_BROADCAST_AT.get(wid, 0.0)
    rl_ok = (now_mono - last_rl) * 1000.0 >= POSITIONS_MIN_INTERVAL_MS

    async with _wh_lock(wid):
        now_mono = loop.time()
        need_keepalive = need_keepalive or ((now_mono - _LAST_ANY_SENT_AT.get(wid, 0.0)) * 1000.0 >= POSITIONS_KEEPALIVE_MS)
        rl_ok = rl_ok and ((now_mono - _LAST_POS_BROADCAST_AT.get(wid, 0.0)) * 1000.0 >= POSITIONS_MIN_INTERVAL_MS)

        cur_ver = _WH_SNAPSHOT_VER.get(wid, 0)
        last_sent_ver = _WH_LAST_SENT_VER.get(wid, -1)
        snap_dict = _wh_snapshot(wid)

        has_changes = cur_ver != last_sent_ver
        have_data = bool(snap_dict)

        if not have_data and not need_keepalive:
            return

        payload_ts = datetime.now(timezone.utc).isoformat()

        if has_changes and rl_ok and have_data:
            if POSITIONS_DIFFS:
                changed, removed = _calc_diff_payload(wid, snap_dict)
                if changed or removed:
                    await _emit({
                        "type": "robot.positions.diff",
                        "warehouse_id": wid,
                        "version": cur_ver,
                        "base_version": last_sent_ver,
                        "changed": changed,
                        "removed": removed,
                        "ts": payload_ts,
                    })
                    _remember_last_sent_map(wid, snap_dict)
                    _WH_LAST_SENT_VER[wid] = cur_ver
                    _LAST_POS_BROADCAST_AT[wid] = loop.time()
                    _LAST_ANY_SENT_AT[wid] = _LAST_POS_BROADCAST_AT[wid]
                    return
            await _emit({
                "type": "robot.positions",
                "warehouse_id": wid,
                "robots": list(snap_dict.values()),
                "version": cur_ver,
                "ts": payload_ts,
            })
            _remember_last_sent_map(wid, snap_dict)
            _WH_LAST_SENT_VER[wid] = cur_ver
            _LAST_POS_BROADCAST_AT[wid] = loop.time()
            _LAST_ANY_SENT_AT[wid] = _LAST_POS_BROADCAST_AT[wid]
            return

        if need_keepalive:
            if POSITIONS_DIFFS and not KEEPALIVE_FULL:
                await _emit({
                    "type": "robot.positions.keepalive",
                    "warehouse_id": wid,
                    "version": cur_ver,
                    "robot_count": len(snap_dict),
                    "ts": payload_ts,
                })
            else:
                await _emit({
                    "type": "robot.positions",
                    "warehouse_id": wid,
                    "robots": list(snap_dict.values()),
                    "version": cur_ver,
                    "ts": payload_ts,
                })
                _remember_last_sent_map(wid, snap_dict)
                _WH_LAST_SENT_VER[wid] = cur_ver
                _LAST_POS_BROADCAST_AT[wid] = loop.time()
            _LAST_ANY_SENT_AT[wid] = loop.time()

async def _emit_positions_snapshot_force(wid: str) -> None:
    if USE_REDIS_COORD:
        return
    async with _wh_lock(wid):
        snap_dict = _wh_snapshot(wid)
        payload = list(snap_dict.values())
        cur_ver = _WH_SNAPSHOT_VER.get(wid, 0)
    if not payload:
        return
    await _emit({
        "type": "robot.positions",
        "warehouse_id": wid,
        "robots": payload,
        "version": cur_ver,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    loop = asyncio.get_running_loop()
    _remember_last_sent_map(wid, snap_dict)
    _WH_LAST_SENT_VER[wid] = cur_ver
    _LAST_POS_BROADCAST_AT[wid] = loop.time()
    _LAST_ANY_SENT_AT[wid] = _LAST_POS_BROADCAST_AT[wid]

async def _positions_broadcast_loop(wid: str) -> None:
    interval = max(100, POSITIONS_BROADCAST_INTERVAL_MS) / 1000.0
    try:
        while True:
            await asyncio.sleep(interval)

            if USE_REDIS_COORD:
                if _SHARD_IDX != COORDINATOR_SHARD_INDEX:
                    continue
                r = await _get_redis()
                hkey = _r_key_robots_hash(wid)
                ver_key = _r_key_robots_ver(wid)
                lastsent_key = _r_key_robots_lastmap(wid)

                data = await r.hgetall(hkey)
                if not data:
                    continue
                robots = []
                for rid, s in data.items():
                    try:
                        robots.append(json.loads(s))
                    except Exception:
                        pass

                cur_ver = int(await r.incr(ver_key))
                payload_ts = datetime.now(timezone.utc).isoformat()

                if POSITIONS_DIFFS:
                    last_json = await r.get(lastsent_key)
                    last_map = {}
                    if last_json:
                        try:
                            last_map = json.loads(last_json)
                        except Exception:
                            last_map = {}
                    cur_map = {item["robot_id"]: item for item in robots}
                    changed = [v for k, v in cur_map.items() if last_map.get(k) != v]
                    removed = [k for k in last_map.keys() if k not in cur_map]

                    if changed or removed:
                        await _emit({
                            "type": "robot.positions.diff",
                            "warehouse_id": wid,
                            "version": cur_ver,
                            "base_version": cur_ver - 1,
                            "changed": changed,
                            "removed": removed,
                            "ts": payload_ts,
                        })
                        await r.set(lastsent_key, json.dumps(cur_map))
                else:
                    await _emit({
                        "type": "robot.positions",
                        "warehouse_id": wid,
                        "robots": robots,
                        "version": cur_ver,
                        "ts": payload_ts,
                    })
                    await r.set(lastsent_key, json.dumps({x["robot_id"]: x for x in robots}))
                continue

            # local mode
            loop = asyncio.get_running_loop()
            now_mono = loop.time()

            async with _wh_lock(wid):
                cur_ver = _WH_SNAPSHOT_VER.get(wid, 0)
                last_sent_ver = _WH_LAST_SENT_VER.get(wid, -1)
                snap_dict = _wh_snapshot(wid)
                have_data = bool(snap_dict)
                last_any = _LAST_ANY_SENT_AT.get(wid, 0.0)
                need_keepalive = (now_mono - last_any) * 1000.0 >= POSITIONS_MAX_INTERVAL_MS
                changed = cur_ver != last_sent_ver

                if not have_data:
                    continue

                payload_ts = datetime.now(timezone.utc).isoformat()

                if changed:
                    if POSITIONS_DIFFS:
                        changed_items, removed = _calc_diff_payload(wid, snap_dict)
                        if changed_items or removed:
                            await _emit({
                                "type": "robot.positions.diff",
                                "warehouse_id": wid,
                                "version": cur_ver,
                                "base_version": last_sent_ver,
                                "changed": changed_items,
                                "removed": removed,
                                "ts": payload_ts,
                            })
                            _remember_last_sent_map(wid, snap_dict)
                            _WH_LAST_SENT_VER[wid] = cur_ver
                    else:
                        await _emit({
                            "type": "robot.positions",
                            "warehouse_id": wid,
                            "robots": list(snap_dict.values()),
                            "version": cur_ver,
                            "ts": payload_ts,
                        })
                        _remember_last_sent_map(wid, snap_dict)
                        _WH_LAST_SENT_VER[wid] = cur_ver

                    _LAST_POS_BROADCAST_AT[wid] = now_mono
                    _LAST_ANY_SENT_AT[wid] = now_mono
                    continue

                if need_keepalive:
                    if POSITIONS_DIFFS and not KEEPALIVE_FULL:
                        await _emit({
                            "type": "robot.positions.keepalive",
                            "warehouse_id": wid,
                            "version": cur_ver,
                            "robot_count": len(snap_dict),
                            "ts": payload_ts,
                        })
                    else:
                        await _emit({
                            "type": "robot.positions",
                            "warehouse_id": wid,
                            "robots": list(snap_dict.values()),
                            "version": cur_ver,
                            "ts": payload_ts,
                        })
                        _remember_last_sent_map(wid, snap_dict)
                        _WH_LAST_SENT_VER[wid] = cur_ver

                    _LAST_POS_BROADCAST_AT[wid] = now_mono
                    _LAST_ANY_SENT_AT[wid] = now_mono
    except asyncio.CancelledError:
        pass

def _ensure_positions_broadcaster_started(wid: str) -> None:
    if wid in _WH_POS_TASK and not _WH_POS_TASK[wid].done():
        return
    _WH_POS_TASK[wid] = asyncio.create_task(_positions_broadcast_loop(wid))

async def _stop_positions_broadcaster(wid: str) -> None:
    t = _WH_POS_TASK.pop(wid, None)
    if t:
        t.cancel()
        try:
            await t
        except Exception:
            pass

# =========================
# 22) Warmup / sync snapshot + seed staleness ZSET
# =========================
async def _warmup_or_sync_snapshot(session: AsyncSession, wid: str, robot_ids: Optional[List[str]] = None) -> None:
    if robot_ids is None:
        r = await session.execute(select(Robot.id).where(Robot.warehouse_id == wid))
        robot_ids = list(r.scalars().all())
    if robot_ids:
        res = await session.execute(
            select(Robot.id, Robot.current_row, Robot.current_shelf, Robot.battery_level, Robot.status)
            .where(Robot.warehouse_id == wid, Robot.id.in_(robot_ids))
        )
        db_rows = {rid: (shelf, row, battery, status) for rid, row, shelf, battery, status in res.all()}
    else:
        db_rows = {}
    changed = False
    async with _wh_lock(wid):
        snap = _wh_snapshot(wid)
        if robot_ids is not None:
            for rid in list(snap.keys()):
                if rid not in robot_ids:
                    snap.pop(rid, None)
                    changed = True
        now_iso = datetime.now(timezone.utc).isoformat()
        for rid in robot_ids:
            x, y, battery, status = db_rows.get(rid, (0, 0, 0.0, "idle"))
            _ROBOT_WH[rid] = wid
            x_int = int(x or 0)
            y_int = int(y or 0)
            new_item = {
                "robot_id": rid,
                "x": x_int,
                "y": y_int,
                "shelf": shelf_num_to_str(x_int),
                "battery_level": round(float(battery or 0.0), 1),
                "status": status or "idle",
                "updated_at": (snap.get(rid) or {}).get("updated_at") or now_iso,
            }
            if snap.get(rid) != new_item:
                snap[rid] = new_item
                changed = True
        if changed:
            _WH_SNAPSHOT_VER[wid] = _WH_SNAPSHOT_VER.get(wid, 0) + 1

    # Однократная инициализация ZSET «давности» (без лишних SQL в будущем)
    await _seed_staleness_zset(session, wid)

# =========================
# 23) Fast scan loop (unchanged, minor cleanups)
# =========================
async def _fast_scan_loop(wid: str) -> None:
    interval = max(5, FAST_SCAN_INTERVAL_MS) / 1000.0
    try:
        while True:
            await asyncio.sleep(interval)
            now = datetime.now(timezone.utc)

            scan_rids = [
                item["robot_id"] for item in _wh_snapshot(wid).values()
                if (item.get("status") or "").lower() == "scanning"
            ]
            for rid in scan_rids:
                if _SCANNING_FINISHING.get(rid):
                    continue
                if rid not in _SCANNING_UNTIL:
                    _SCANNING_STARTED_AT[rid] = now
                    _SCANNING_UNTIL[rid] = now
                    snap = _wh_snapshot(wid).get(rid) or {}
                    _SCANNING_CELL.setdefault(rid, (int(snap.get("x") or 0), int(snap.get("y") or 0)))

                start_at = _SCANNING_STARTED_AT.get(rid)
                if start_at and (now - start_at).total_seconds() * 1000.0 > SCAN_MAX_DURATION_MS:
                    try:
                        async with AppSession() as s:
                            async with s.begin():
                                rres = await s.execute(
                                    select(Robot).options(load_only(
                                        Robot.id, Robot.warehouse_id, Robot.status,
                                        Robot.battery_level, Robot.current_row, Robot.current_shelf,
                                    )).where(Robot.id == rid)
                                )
                                robot = rres.scalar_one_or_none()
                                if robot:
                                    await _safe_finish_scan(s, robot)
                                    await s.flush()
                                    _update_wh_snapshot_from_robot(robot)
                                    await _maybe_emit_positions_snapshot_inmem(robot.warehouse_id)
                    except Exception as e:
                        print(f"⚠️ fast-scan watchdog error (wh={wid}, rid={rid}): {e}", flush=True)
                    continue

                until = _SCANNING_UNTIL.get(rid)
                if until and now >= until:
                    try:
                        async with AppSession() as s:
                            async with s.begin():
                                rres = await s.execute(
                                    select(Robot).options(load_only(
                                        Robot.id, Robot.warehouse_id, Robot.status,
                                        Robot.battery_level, Robot.current_row, Robot.current_shelf,
                                    )).where(Robot.id == rid)
                                )
                                robot = rres.scalar_one_or_none()
                                if robot:
                                    await _safe_finish_scan(s, robot)
                                    await s.flush()
                                    _update_wh_snapshot_from_robot(robot)
                                    await _maybe_emit_positions_snapshot_inmem(robot.warehouse_id)
                    except Exception as e:
                        print(f"⚠️ fast-scan error (wh={wid}, rid={rid}): {e}", flush=True)
    except asyncio.CancelledError:
        pass

def _ensure_fast_scan_task_started(wid: str) -> None:
    if not FAST_SCAN_LOOP:
        return
    if wid in _WH_FASTSCAN_TASK and not _WH_FASTSCAN_TASK[wid].done():
        return
    _WH_FASTSCAN_TASK[wid] = asyncio.create_task(_fast_scan_loop(wid))

async def _stop_fast_scan_task(wid: str) -> None:
    t = _WH_FASTSCAN_TASK.pop(wid, None)
    if t:
        t.cancel()
        try:
            await t
        except Exception:
            pass

# =========================
# 24) Scheduler: robot selection window
# =========================
def _select_robot_batch(wid: str, robot_ids: List[str]) -> List[str]:
    if not robot_ids:
        return []
    scanning = [rid for rid in robot_ids if (rid in _SCANNING_UNTIL) or _is_scanning_in_snapshot(wid, rid)]
    scanning_set = set(scanning)
    normal = [rid for rid in robot_ids if rid not in scanning_set]

    win = max(ROBOTS_PER_TICK - len(scanning), 0)
    if win <= 0:
        return scanning
    n = len(normal)
    if n == 0:
        return scanning
    off = _WH_ROBOT_OFFSET.get(wid, 0) % n
    if off + win <= n:
        batch = normal[off:off + win]
    else:
        batch = normal[off:] + normal[:(off + win) % n]
    _WH_ROBOT_OFFSET[wid] = (off + win) % n
    return scanning + batch

# =========================
# 25) Watcher loops
# =========================
async def _dispose_async_engine_if_any():
    try:
        from app.db.session import async_engine as _engine
    except Exception:
        _engine = getattr(AppSession, "bind", None)
    try:
        if isinstance(_engine, AsyncEngine):
            await _engine.dispose()
    except Exception:
        pass

async def _run_warehouse(wid: str) -> None:
    sema = asyncio.Semaphore(ROBOTS_CONCURRENCY)
    tick = 0
    _set_shard(0, 1)
    _ensure_fast_scan_task_started(wid)
    _ensure_positions_broadcaster_started(wid)
    try:
        while True:
            try:
                async with AppSession() as session:
                    r = await session.execute(select(Robot.id).where(Robot.warehouse_id == wid))
                    all_robot_ids = list(r.scalars().all())
                if not all_robot_ids:
                    await asyncio.sleep(TICK_INTERVAL)
                    continue

                if all_robot_ids and not _WH_SNAPSHOT.get(wid):
                    async with AppSession() as s:
                        await _warmup_or_sync_snapshot(s, wid, all_robot_ids)
                        await _emit_positions_snapshot_force(wid)
                        if EMIT_AUTOSEND_INIT:
                            await _emit_product_scans_init(wid)

                async with AppSession() as s:
                    await _warmup_or_sync_snapshot(s, wid, all_robot_ids)

                robot_ids = _select_robot_batch(wid, all_robot_ids)
                tid = _next_tick_id(wid)

                async def run_one(rid: str):
                    async with sema:
                        async with AppSession() as s:
                            async with s.begin():
                                await _robot_tick(s, rid, tick_id=tid)

                await asyncio.gather(*[run_one(rid) for rid in robot_ids])

                tick += 1
                if tick % 20 == 0:
                    print(f"[{datetime.now().isoformat()}] wh={wid} tick={tick} robots_tick={len(robot_ids)}/{len(all_robot_ids)}", flush=True)

                await asyncio.sleep(TICK_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"⚠️ warehouse loop error (wh={wid}): {e}", flush=True)
                await asyncio.sleep(0.5)
    finally:
        await _stop_fast_scan_task(wid)
        await _stop_positions_broadcaster(wid)

async def run_robot_watcher() -> None:
    print(f"🚀 watcher started pid={os.getpid()} interval={TICK_INTERVAL}s", flush=True)
    tasks: Dict[str, asyncio.Task] = {}
    try:
        while True:
            try:
                async with AppSession() as session:
                    rows = await session.execute(
                        select(Warehouse.id).join(Robot, Robot.warehouse_id == Warehouse.id).distinct()
                    )
                    wh_ids = set(rows.scalars().all())

                for wid in wh_ids:
                    if wid not in tasks or tasks[wid].done():
                        tasks[wid] = asyncio.create_task(_run_warehouse(wid))

                for wid in list(tasks.keys()):
                    if wid not in wh_ids:
                        tasks[wid].cancel()
                        try:
                            await tasks[wid]
                        except Exception:
                            pass
                        tasks.pop(wid, None)
                        _CLAIMED.pop(wid, None)
                        _WH_SNAPSHOT.pop(wid, None)
                        _WH_SNAPSHOT_VER.pop(wid, None)
                        _WH_LAST_SENT_VER.pop(wid, None)
                        _WH_LAST_SENT_MAP.pop(wid, None)
                        _LAST_POS_BROADCAST_AT.pop(wid, None)
                        _LAST_ANY_SENT_AT.pop(wid, None)
                        _ELIGIBLE_CACHE.pop(wid, None)
                        _WH_TICK_COUNTER.pop(wid, None)
                        _WH_ROBOT_OFFSET.pop(wid, None)
                        _WH_LOCKS.pop(wid, None)
                        await _stop_fast_scan_task(wid)
                        await _stop_positions_broadcaster(wid)

                await asyncio.sleep(TICK_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"⚠️ watcher loop error: {e}", flush=True)
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        print("🛑 watcher cancelled", flush=True)
    finally:
        for wid, t in list(tasks.items()):
            t.cancel()
            try:
                await t
            except Exception:
                pass
            await _stop_fast_scan_task(wid)
            await _stop_positions_broadcaster(wid)
        await close_bus_for_current_loop()
        await _dispose_async_engine_if_any()
        await _close_redis()
        print("✅ watcher stopped", flush=True)

# =========================
# 26) Multiprocessing watcher (sharded)
# =========================
MP_START_METHOD = os.getenv("MP_START_METHOD", "spawn")
MAX_WAREHOUSE_PROCS = int(os.getenv("MAX_WAREHOUSE_PROCS", "0"))
ROBOTS_PER_PROC = int(os.getenv("ROBOTS_PER_PROC", "3"))

@dataclass
class _WhProc:
    proc: mp.Process
    stop_evt: mp.Event

async def _list_active_warehouses() -> Set[str]:
    async with AppSession() as session:
        rows = await session.execute(
            select(Warehouse.id).join(Robot, Robot.warehouse_id == Warehouse.id).distinct()
        )
        return set(rows.scalars().all())

async def _graceful_wait(condition_fn, timeout: float, poll: float = 0.1) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if condition_fn():
            return True
        await asyncio.sleep(poll)
    return condition_fn()

def _warehouse_process_entry(wid: str, shard_idx: int, shard_count: int, stop_evt: mp.Event) -> None:
    try:
        print(
            "[diag] spawn start | "
            f"SQLALCHEMY_DISABLE_CEXT={os.environ.get('SQLALCHEMY_DISABLE_CEXT')} "
            f"GREENLET_USE_GC={os.environ.get('GREENLET_USE_GC')} "
            f"sitecustomize_loaded={bool(pkgutil.find_loader('sitecustomize'))} "
            f"sa_cyext_loaded={any(m.startswith('sqlalchemy.cyextension') for m in sys.modules)}",
            flush=True
        )
        asyncio.run(_run_warehouse_until_event(wid, shard_idx, shard_count, stop_evt))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"⚠️ worker({wid}) crashed: {e}", flush=True)
    finally:
        try:
            asyncio.run(close_bus_for_current_loop())
        except Exception:
            pass
        try:
            asyncio.run(_dispose_async_engine_if_any())
        except Exception:
            pass
        try:
            asyncio.run(_close_redis())
        except Exception:
            pass
        print(f"🧹 worker({wid}) stopped", flush=True)

async def _run_warehouse_until_event(wid: str, shard_idx: int, shard_count: int, stop_evt: mp.Event) -> None:
    sema = asyncio.Semaphore(ROBOTS_CONCURRENCY)
    tick = 0
    _set_shard(shard_idx, shard_count)
    print(f"🏭 worker({wid}) shard={shard_idx+1}/{max(1, shard_count)} started pid={os.getpid()} interval={TICK_INTERVAL}s", flush=True)
    _ensure_fast_scan_task_started(wid)

    if USE_REDIS_COORD:
        if shard_idx == COORDINATOR_SHARD_INDEX:
            _ensure_positions_broadcaster_started(wid)
    else:
        _ensure_positions_broadcaster_started(wid)

    def _stopping() -> bool:
        return stop_evt.is_set()

    try:
        while not _stopping():
            try:
                async with AppSession() as session:
                    r = await session.execute(select(Robot.id).where(Robot.warehouse_id == wid))
                    all_robot_ids = sorted(list(r.scalars().all()))
                if shard_count > 1:
                    all_robot_ids = [rid for i, rid in enumerate(all_robot_ids) if (i % shard_count) == shard_idx]
                if not all_robot_ids:
                    await asyncio.sleep(TICK_INTERVAL)
                    continue

                if all_robot_ids and not _WH_SNAPSHOT.get(wid):
                    async with AppSession() as s:
                        await _warmup_or_sync_snapshot(s, wid, all_robot_ids)
                        await _emit_positions_snapshot_force(wid)
                        if (not USE_REDIS_COORD) or (USE_REDIS_COORD and shard_idx == COORDINATOR_SHARD_INDEX):
                            if EMIT_AUTOSEND_INIT:
                                await _emit_product_scans_init(wid)

                async with AppSession() as s:
                    await _warmup_or_sync_snapshot(s, wid, all_robot_ids)

                robot_ids = _select_robot_batch(wid, all_robot_ids)
                tid = _next_tick_id(wid)

                async def run_one(rid: str):
                    async with sema:
                        async with AppSession() as s:
                            async with s.begin():
                                await _robot_tick(s, rid, tick_id=tid)

                await asyncio.gather(*[run_one(rid) for rid in robot_ids])

                tick += 1
                if tick % 20 == 0:
                    print(f"[{datetime.now().isoformat()}] wh={wid} shard={shard_idx+1}/{shard_count} tick={tick} robots_tick={len(robot_ids)}/{len(all_robot_ids)}", flush=True)

                await asyncio.sleep(TICK_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"⚠️ warehouse loop error (wh={wid} shard={shard_idx+1}/{shard_count}): {e}", flush=True)
                await asyncio.sleep(0.5)
    finally:
        await _stop_fast_scan_task(wid)
        if not USE_REDIS_COORD or (USE_REDIS_COORD and shard_idx == COORDINATOR_SHARD_INDEX):
            await _stop_positions_broadcaster(wid)
        _CLAIMED.pop(wid, None)
        _WH_SNAPSHOT.pop(wid, None)
        _WH_SNAPSHOT_VER.pop(wid, None)
        _WH_LAST_SENT_VER.pop(wid, None)
        _WH_LAST_SENT_MAP.pop(wid, None)
        _LAST_POS_BROADCAST_AT.pop(wid, None)
        _LAST_ANY_SENT_AT.pop(wid, None)
        _ELIGIBLE_CACHE.pop(wid, None)
        _WH_TICK_COUNTER.pop(wid, None)
        _WH_ROBOT_OFFSET.pop(wid, None)
        _WH_LOCKS.pop(wid, None)
        await close_bus_for_current_loop()
        await _dispose_async_engine_if_any()
        await _close_redis()

async def run_robot_watcher_mproc() -> None:
    mp.set_start_method(MP_START_METHOD, force=True)
    print(f"🚀 MP watcher started pid={os.getpid()} method={MP_START_METHOD} interval={TICK_INTERVAL}s", flush=True)

    procs: Dict[str, _WhProc] = {}
    stop = asyncio.Event()

    def _on_signal(sig, _frame=None):
        print(f"🛑 MP watcher got signal {sig}", flush=True)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _on_signal)
        except Exception:
            pass

    try:
        while not stop.is_set():
            try:
                wh_ids = await _list_active_warehouses()

                wh_robot_counts: Dict[str, int] = {}
                async with AppSession() as session:
                    rows = await session.execute(
                        select(Warehouse.id, func.count(Robot.id))
                        .join(Robot, Robot.warehouse_id == Warehouse.id)
                        .group_by(Warehouse.id)
                    )
                    for wid, cnt in rows.all():
                        wh_robot_counts[wid] = int(cnt)

                for wid in sorted(wh_ids):
                    total = wh_robot_counts.get(wid, 0)
                    shard_count = max(1, (total + ROBOTS_PER_PROC - 1) // ROBOTS_PER_PROC) if total > 0 else 0
                    alive_global = len([p for p in procs.values() if p.proc.is_alive()])

                    for shard_idx in range(shard_count):
                        key = f"{wid}:{shard_idx}/{shard_count}"
                        if key in procs and procs[key].proc.is_alive():
                            continue
                        if MAX_WAREHOUSE_PROCS > 0 and alive_global >= MAX_WAREHOUSE_PROCS:
                            break
                        stop_evt = mp.Event()
                        p = mp.Process(
                            target=_warehouse_process_entry,
                            args=(wid, shard_idx, shard_count, stop_evt),
                            name=f"wh-{wid[:6]}-s{shard_idx+1}of{shard_count}",
                            daemon=False,
                        )
                        p.start()
                        procs[key] = _WhProc(proc=p, stop_evt=stop_evt)
                        alive_global += 1
                        print(f"▶️ started worker for wh={wid} shard={shard_idx+1}/{shard_count} pid={p.pid}", flush=True)

                active_keys = set()
                for wid in sorted(wh_ids):
                    total = wh_robot_counts.get(wid, 0)
                    shard_count = max(1, (total + ROBOTS_PER_PROC - 1) // ROBOTS_PER_PROC) if total > 0 else 0
                    for shard_idx in range(shard_count):
                        active_keys.add(f"{wid}:{shard_idx}/{shard_count}")

                for key in list(procs.keys()):
                    wid = key.split(":", 1)[0]
                    if (wid not in wh_ids) or (key not in active_keys):
                        wp = procs.pop(key, None)
                        if not wp:
                            continue
                        print(f"⏹ stopping worker {key}", flush=True)
                        try:
                            wp.stop_evt.set()
                        except Exception:
                            pass
                        wp.proc.join(timeout=10)
                        if wp.proc.is_alive():
                            print(f"⛔ force terminate {key}", flush=True)
                            wp.proc.terminate()
                            wp.proc.join(timeout=5)

                for key, wp in list(procs.items()):
                    if not wp.proc.is_alive():
                        procs.pop(key, None)

                await asyncio.sleep(TICK_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"⚠️ MP watcher loop error: {e}", flush=True)
                await asyncio.sleep(0.5)
    finally:
        print("🧹 MP watcher shutting down...", flush=True)
        for key, wp in list(procs.items()):
            try:
                wp.stop_evt.set()
            except Exception:
                pass
        await _graceful_wait(lambda: all(not wp.proc.is_alive() for wp in procs.values()), timeout=12.0, poll=0.2)
        for key, wp in list(procs.items()):
            if wp.proc.is_alive():
                print(f"⛔ force terminate {key}", flush=True)
                wp.proc.terminate()
        for key, wp in list(procs.items()):
            try:
                wp.proc.join(timeout=3)
            except Exception:
                pass
        await close_bus_for_current_loop()
        await _dispose_async_engine_if_any()
        await _close_redis()
        print("✅ MP watcher stopped", flush=True)
