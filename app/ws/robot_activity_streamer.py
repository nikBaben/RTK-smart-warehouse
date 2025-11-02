from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Protocol, AsyncContextManager, Callable

from app.events.bus import get_bus_for_current_loop, COMMON_CH

try:
    from app.ws.ws_manager import manager  # type: ignore
except Exception:
    manager = None  # type: ignore


ACTIVE_STATUSES = ("idle", "scanning")
POINTS_COUNT = 7                                    # ровно 7 точек
BUCKET_SEC = 600                                    # 10 минут
WINDOW_MIN = POINTS_COUNT * (BUCKET_SEC // 60)      # 70 минут
_last_bucket_sent: Dict[str, datetime] = {}         # warehouse_id -> last emitted bucket_end (UTC)
_next_allowed_emit: Dict[str, datetime] = {}        # warehouse_id -> next allowed publish (UTC)

class RobotHistoryRepoProto(Protocol):
    async def total_robots(self, warehouse_id: str) -> int: ...
    async def latest_history_timestamp(self, warehouse_id: str) -> Optional[datetime]: ...
    async def baseline_statuses_before(self, warehouse_id: str, before_ts: datetime) -> Dict[str, str]: ...
    async def events_in_window(
        self,
        warehouse_id: str,
        start_inclusive: datetime,
        end_inclusive: datetime,
    ) -> List[Tuple[str, str, datetime]]: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]: ...


#служебные утилиты
def _ensure_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)

def _floor(ts: datetime, bucket_sec: int) -> datetime:
    ts = _ensure_utc(ts)
    s = int(ts.timestamp())
    return datetime.fromtimestamp(s - s % bucket_sec, tz=timezone.utc)

def _axis_from_last(now_like: datetime, buckets: int, bucket_sec: int) -> List[datetime]:
    end = _floor(now_like, bucket_sec)
    start = end - timedelta(seconds=bucket_sec * (buckets - 1))
    t = start
    out: List[datetime] = []
    while t <= end:
        out.append(t)
        t += timedelta(seconds=bucket_sec)
    return out[-buckets:]

def _bucket_end_of(ts: datetime, bucket_sec: int) -> datetime:
    return _floor(ts, bucket_sec)

def _carry_forward_active_counts(
    axis: List[datetime],
    baseline: Dict[str, str],
    events: List[Tuple[str, str, datetime]],
    total_robots: int,
) -> List[Tuple[str, float]]:
    state: Dict[str, str] = dict(baseline)
    idx = 0
    n = len(events)
    out: List[Tuple[str, float]] = []

    if total_robots <= 0:
        return [(t.isoformat(), 0.0) for t in axis]

    for bucket_end in axis:
        while idx < n and events[idx][2] <= bucket_end:
            rid, status, _ts = events[idx]
            state[rid] = status
            idx += 1
        active = sum(1 for s in state.values() if s in ACTIVE_STATUSES)
        pct = round((active / total_robots) * 100.0, 2)
        out.append((bucket_end.isoformat(), pct))
    return out


#публикации
async def publish_robot_activity_series_from_history(
    repo: RobotHistoryRepoProto,
    warehouse_id: str,
    *,
    force: bool = False,
):
    bus = await get_bus_for_current_loop()
    now_srv = datetime.now(timezone.utc)

    next_allowed = _next_allowed_emit.get(warehouse_id)
    if not force and next_allowed is not None and now_srv < next_allowed:
        return

    bucket_end = _bucket_end_of(now_srv, BUCKET_SEC)
    if not force and _last_bucket_sent.get(warehouse_id) == bucket_end:
        return

    axis = _axis_from_last(now_srv, POINTS_COUNT, BUCKET_SEC)
    start, end = axis[0], axis[-1]

    last_ts = await repo.latest_history_timestamp(warehouse_id)
    if last_ts is None:
        series = [(t.isoformat(), 0.0) for t in axis]
        await bus.publish(COMMON_CH, {
            "type": "robot.activity_series",
            "warehouse_id": warehouse_id,
            "window_min": WINDOW_MIN,
            "bucket_sec": BUCKET_SEC,
            "series": series,
            "ts": end.isoformat(),
            "total_robots": 0,
        })
        _last_bucket_sent[warehouse_id] = bucket_end
        _next_allowed_emit[warehouse_id] = now_srv + timedelta(seconds=BUCKET_SEC)
        return

    total = await repo.total_robots(warehouse_id)
    baseline = await repo.baseline_statuses_before(warehouse_id, start)
    events = await repo.events_in_window(warehouse_id, start, end)
    series = _carry_forward_active_counts(axis, baseline, events, total)

    await bus.publish(COMMON_CH, {
        "type": "robot.activity_series",
        "warehouse_id": warehouse_id,
        "window_min": WINDOW_MIN,
        "bucket_sec": BUCKET_SEC,
        "series": series,
        "ts": end.isoformat(),
        "total_robots": total,
    })
    _last_bucket_sent[warehouse_id] = bucket_end
    _next_allowed_emit[warehouse_id] = now_srv + timedelta(seconds=BUCKET_SEC)


#выбор активных складов
async def _get_active_warehouses_by_ws() -> List[str]:
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:
        return []

async def _get_active_warehouses_by_repo(repo: RobotHistoryRepoProto) -> List[str]:
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:
        return []


#Вспомогательная задержка до края бакета
async def _sleep_until_next_bucket() -> None:
    now = datetime.now(timezone.utc)
    next_edge = _floor(now, BUCKET_SEC) + timedelta(seconds=BUCKET_SEC)
    await asyncio.sleep(max((next_edge - now).total_seconds(), 0.0))


#Фоновая задача
async def continuous_robot_activity_history_streamer(
    repo_provider: Callable[[], AsyncContextManager[RobotHistoryRepoProto]],
    *,
    interval: float = 600,
    use_ws_rooms: bool = False,
):
    print(f"continuous_robot_activity_history_streamer(interval={interval}, use_ws_rooms={use_ws_rooms})")
    try:
        await _sleep_until_next_bucket()
        while True:
            try:
                async with repo_provider() as repo:
                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wh in wh_ids:
                                await publish_robot_activity_series_from_history(repo, wh)
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)
                        for wh in wh_ids:
                            await publish_robot_activity_series_from_history(repo, wh)
            except Exception as inner_err:
                print(f"continuous_robot_activity_history_streamer inner error: {inner_err}")
            await _sleep_until_next_bucket()
    except asyncio.CancelledError:
        print("continuous_robot_activity_history_streamer cancelled")
    except Exception as e:
        print(f"continuous_robot_activity_history_streamer fatal error: {e}")


#Точечное обновление после записи в RobotHistory
async def publish_robot_activity_on_history_event(
    repo: RobotHistoryRepoProto,
    history_id: str,
):
    try:
        wh = await repo.get_warehouse_id_by_history_id(history_id)
        if wh:
            await publish_robot_activity_series_from_history(repo, wh, force=True)
    except Exception as e:
        print(f"publish_robot_activity_on_history_event({history_id}) error: {e}")
