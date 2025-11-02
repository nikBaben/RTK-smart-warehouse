from __future__ import annotations

import os
import json
import asyncio
from typing import Dict, Optional

try:
    import redis.asyncio as aioredis 
except Exception:              
    import aioredis                     # type: ignore


class EventBus:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        if not self._redis:
            self._redis = aioredis.from_url(
                self._dsn,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,  
                retry_on_timeout=True,
            )

    async def publish(self, channel: str, payload: dict) -> None:
        if not self._redis:
            await self.connect()
        await self._redis.publish(channel, json.dumps(payload))

    async def pubsub(self):
        if not self._redis:
            await self.connect()
        return self._redis.pubsub()

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

# Каналы
ROBOT_CH = "ws:robot"
COMMON_CH = "ws:common"

REDIS_DSN = os.getenv("REDIS_DSN", "redis://myapp-redis:6379/0")

_buses: Dict[int, EventBus] = {}

async def get_bus_for_current_loop() -> EventBus:
    """
    Возвращает EventBus, привязанный к ТЕКУЩЕМУ event loop’у.
    Это устраняет ошибку "Future attached to a different loop".
    """
    loop = asyncio.get_running_loop()
    key = id(loop)
    bus = _buses.get(key)
    if not bus:
        bus = EventBus(REDIS_DSN)
        await bus.connect()
        _buses[key] = bus
    return bus

#Закрывает и удаляет bus для текущего loop’а (аккуратная остановка потока).
async def close_bus_for_current_loop() -> None:
    loop = asyncio.get_running_loop()
    key = id(loop)
    bus = _buses.pop(key, None)
    if bus:
        await bus.close()


__all__ = [
    "EventBus",
    "get_bus_for_current_loop",
    "close_bus_for_current_loop",
    "ROBOT_CH",
    "COMMON_CH",
]
