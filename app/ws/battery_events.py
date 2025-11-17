# app/events/battery_events.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncContextManager, Callable, List, Optional, Protocol

from app.events.bus import get_bus_for_current_loop, COMMON_CH
from app.repositories.protos import RobotRepositoryProto
from app.repositories.bundle import robot_repo_provider

try:
    # Не обязательно доступен (например, в воркере без WS)
    from app.ws.ws_manager import manager  # type: ignore
except Exception:  # pragma: no cover
    manager = None  # type: ignore


__all__ = [
    "publish_robot_avg_snapshot",
    "publish_robot_battery_changed",
    "publish_robot_deleted",
    "continuous_robot_avg_streamer",
    "default_robot_repo_provider",
]

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """UTC-штамп в ISO 8601, например '2025-11-03T10:15:30.123456+00:00'."""
    return datetime.now(timezone.utc).isoformat()


# --- Локальный протокол для методов, нужных только этому модулю ----------------
class RobotBatteryRepoProto(Protocol):
    async def avg_battery_by_warehouse(self, warehouse_id: str) -> float: ...
    async def get_distinct_warehouse_ids(self) -> List[str]: ...
    async def get_warehouse_id_by_robot_id(self, robot_id: str) -> Optional[str]: ...


# Тип репозитория, который мы ожидаем от провайдера:
# экземпляр конкретного RobotRepository должен реализовывать и базовый
# RobotRepositoryProto (из protos.py), и методы выше (duck typing).
RepoForBattery = RobotRepositoryProto  # для читаемости тип оставим базовым


# --- Утилита-провайдер по умолчанию -------------------------------------------
def default_robot_repo_provider() -> AsyncContextManager[RepoForBattery]:
    """
    Провайдер репозитория роботов на базе твоего robot_repo_provider.
    commit_on_exit=False — чтобы читать в одной транзакции и не коммитить.
    """
    return robot_repo_provider(commit_on_exit=False)


# --- Публикация событий --------------------------------------------------------
async def publish_robot_avg_snapshot(
    repo: RobotBatteryRepoProto, warehouse_id: str
) -> None:
    """
    Публикует 'robot.avg_battery' для указанного склада.
    """
    try:
        avg = await repo.avg_battery_by_warehouse(warehouse_id)
        event = {
            "type": "robot.avg_battery",
            "warehouse_id": warehouse_id,
            "avg_battery": round(float(avg or 0.0), 2),
            "ts": _now_iso(),
        }
        bus = await get_bus_for_current_loop()
        await bus.publish(COMMON_CH, event)
    except Exception as e:  # pragma: no cover
        logger.exception("Ошибка в publish_robot_avg_snapshot(%s): %s", warehouse_id, e)


async def publish_robot_battery_changed(
    repo: RobotBatteryRepoProto, robot_id: str
) -> None:
    """
    Реагирует на изменение батареи конкретного робота:
    определяет склад и публикует новый снэпшот среднего уровня.
    """
    try:
        warehouse_id = await repo.get_warehouse_id_by_robot_id(robot_id)
        if not warehouse_id:
            return
        await publish_robot_avg_snapshot(repo, warehouse_id)
    except Exception as e:  # pragma: no cover
        logger.exception("Ошибка в publish_robot_battery_changed(%s): %s", robot_id, e)


async def publish_robot_deleted(
    repo: RobotBatteryRepoProto, robot_id: str, warehouse_id: str
) -> None:
    """
    Вызывается при удалении робота: перепубликуем среднее по складу.
    """
    try:
        await publish_robot_avg_snapshot(repo, warehouse_id)
    except Exception as e:  # pragma: no cover
        logger.exception("Ошибка в publish_robot_deleted(%s): %s", robot_id, e)


# --- Определение активных складов ---------------------------------------------
async def _get_active_warehouses_by_ws() -> List[str]:
    """
    Если доступен ws-manager, берём идентификаторы комнат как warehouse_id.
    Иначе возвращаем пустой список.
    """
    if manager is None:
        return []
    try:
        rooms = await manager.list_rooms()
        return rooms or []
    except Exception:  # pragma: no cover
        logger.exception("Ошибка получения активных комнат WS")
        return []


async def _get_active_warehouses_by_repo(repo: RobotBatteryRepoProto) -> List[str]:
    """
    Фолбэк: спрашиваем репозиторий о складах, где есть роботы.
    """
    try:
        return await repo.get_distinct_warehouse_ids()
    except Exception:  # pragma: no cover
        logger.exception("Ошибка получения складов из репозитория")
        return []


# --- Периодический стример -----------------------------------------------------
async def continuous_robot_avg_streamer(
    repo_provider: Callable[[], AsyncContextManager[RepoForBattery]] = default_robot_repo_provider,
    *,
    interval: float = 5.0,
    use_ws_rooms: bool = False,
) -> None:
    """
    Периодически публикует 'robot.avg_battery' для активных складов.

    :param repo_provider: фабрика async context manager'а, отдающая репозиторий
                          (обычно default_robot_repo_provider).
    :param interval: период в секундах между итерациями.
    :param use_ws_rooms: если True — берём список складов из WS-менеджера,
                         иначе — спрашиваем репозиторий.
    """
    logger.info(
        "continuous_robot_avg_streamer запущен (interval=%.2fs, use_ws_rooms=%s).",
        interval,
        use_ws_rooms,
    )
    try:
        while True:
            try:
                async with repo_provider() as repo:  # type: ignore[assignment]
                    # repo соответствует RobotBatteryRepoProto по duck typing
                    battery_repo: RobotBatteryRepoProto = repo  # noqa: F841

                    if use_ws_rooms:
                        wh_ids = await _get_active_warehouses_by_ws()
                        if wh_ids:
                            for wid in wh_ids:
                                await publish_robot_avg_snapshot(repo, wid)  # type: ignore[arg-type]
                    else:
                        wh_ids = await _get_active_warehouses_by_repo(repo)  # type: ignore[arg-type]
                        for wid in wh_ids:
                            await publish_robot_avg_snapshot(repo, wid)  # type: ignore[arg-type]
            except Exception as inner_err:  # pragma: no cover
                logger.exception("Ошибка внутри цикла стримера: %s", inner_err)

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logger.info("continuous_robot_avg_streamer остановлен (CancelledError).")
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("Фатальная ошибка в continuous_robot_avg_streamer: %s", e)
