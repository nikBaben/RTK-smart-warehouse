# app/ws/redis_forwarder.py
from __future__ import annotations

import asyncio
import json
import contextlib
from typing import Any, Dict, Optional

from app.events.bus import get_bus_for_current_loop, ROBOT_CH, COMMON_CH
from app.ws.ws_manager import manager


async def _dispatch_to_ws(event: Dict[str, Any]) -> None:
    """
    Отправляет событие во WS-комнату, совпадающую с warehouse_id.
    События без warehouse_id игнорируются (неизвестно куда слать).
    """
    
    wh: Optional[str] = event.get("warehouse_id")
    if not wh:
        # Диагностика: попались события без warehouse_id — они не попадут в комнату
        et = event.get("type")
        #print(f"⚠️ redis_forwarder: skip event without warehouse_id (type={et})", flush=True)
        return
    target_sid: Optional[str] = event.get("unicast_session_id")

    try:
        if target_sid:
            sent = await manager.unicast_json(wh, target_sid, event)
            #print(f"📤 WS unicast: wh={wh} sid={target_sid} type={event.get('type')} sent={sent}", flush=True)
            return

        sent = await manager.broadcast_json(wh, event)
        #print(f"📤 WS send: wh={wh} type={event.get('type')} sent={sent}", flush=True)

    except Exception as e:
        print(f"⚠️ redis_forwarder: broadcast error for wh={wh}: {e}. event={event}", flush=True)

    


async def start_redis_forwarder(
    retry_initial_delay: float = 1.0,
    retry_max_delay: float = 30.0,
) -> None:
    """
    Подписка на Redis Pub/Sub и форвардинг событий в WebSocket-комнаты.
    Работает в ТЕКУЩЕМ event loop'е и автоматически переподключается при ошибках.
    """
    delay = retry_initial_delay

    while True:
        pubsub = None
        try:
            # Берём loop-local EventBus (фабрика сама подключит клиент при первом вызове)
            bus = await get_bus_for_current_loop()
            pubsub = await bus.pubsub()

            # Подписываемся на телеметрию роботов и на общие события
            await pubsub.subscribe(ROBOT_CH, COMMON_CH)
            #print(f"🔌 redis_forwarder: subscribed to channels: {ROBOT_CH}, {COMMON_CH}", flush=True)

            # Сбрасываем бэкофф после успешной подписки
            delay = retry_initial_delay

            # Основной цикл чтения Pub/Sub
            async for msg in pubsub.listen():
                # redis.asyncio публикует служебные сообщения (subscribe/unsubscribe)
                # Нас интересуют только "message"
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "message":
                    continue

                ch = msg.get("channel")
                raw = msg.get("data")
                if not raw:
                    continue

                # Разбор JSON; при ошибке — диагностируем и продолжаем
                try:
                    event = json.loads(raw)
                except Exception:
                    #print(f"⚠️ redis_forwarder: bad JSON from {ch}: {raw!r}", flush=True)
                    continue

                # Диагностика входящего потока (можно выключить, если слишком многословно)
                et = event.get("type")
                wid = event.get("warehouse_id")
                #print(f"📨 redis_forwarder: {ch} ← {et} (warehouse_id={wid})", flush=True)

                # Форвардинг в WS-комнату
                await _dispatch_to_ws(event)

        except asyncio.CancelledError:
            # Корректный shutdown — пробрасываем дальше, cleanup в finally
            raise
        except Exception as e:
            # Логи + экспоненциальный бэкофф при обрывах соединения / ошибках сети
            #print(
               # f"❌ redis_forwarder: connection loop error: {e}. Reconnecting in {delay:.1f}s",
               # flush=True,
            #)
            await asyncio.sleep(delay)
            delay = min(delay * 2, retry_max_delay)

        finally:
            # Пытаемся аккуратно отписаться/закрыть pubsub при реконнекте/остановке
            if pubsub is not None:
                with contextlib.suppress(Exception):
                    await pubsub.unsubscribe(ROBOT_CH, COMMON_CH)
                with contextlib.suppress(Exception):
                    await pubsub.close()
            #print("🔚 redis_forwarder: pubsub closed", flush=True)
