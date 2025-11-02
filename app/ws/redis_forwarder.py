import asyncio
import json
import contextlib
from typing import Any, Dict, Optional
from app.events.bus import get_bus_for_current_loop, ROBOT_CH, COMMON_CH
from app.ws.ws_manager import manager


#Отправляет событие во WS-комнату, совпадающую с warehouse_id.
#События без warehouse_id игнорируются (неизвестно куда слать).
async def _dispatch_to_ws(event: Dict[str, Any]):
    wh: Optional[str] = event.get("warehouse_id")
    if not wh:
        et = event.get("type")
        return

    target_sid: Optional[str] = event.get("unicast_session_id")
    try:
        if target_sid:
            sent = await manager.unicast_json(wh, target_sid, event)
            return

        sent = await manager.broadcast_json(wh, event)
       
    except Exception as e:
        print(f"⚠️ redis_forwarder: broadcast error for wh={wh}: {e}. event={event}", flush=True)

    

#Подписка на Redis Pub/Sub и форвардинг событий в WebSocket-комнаты.
#Работает в ТЕКУЩЕМ event loop'е и автоматически переподключается при ошибках.
async def start_redis_forwarder(retry_initial_delay: float = 1.0,retry_max_delay: float = 30.0):
    delay = retry_initial_delay
    while True:
        pubsub = None
        try:
            bus = await get_bus_for_current_loop()
            pubsub = await bus.pubsub()

            await pubsub.subscribe(ROBOT_CH, COMMON_CH)
            delay = retry_initial_delay

            async for msg in pubsub.listen():
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "message":
                    continue

                ch = msg.get("channel")
                raw = msg.get("data")
                if not raw:
                    continue

                try:
                    event = json.loads(raw)
                except Exception:
                    continue

                et = event.get("type")
                wid = event.get("warehouse_id")

                await _dispatch_to_ws(event)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            await asyncio.sleep(delay)
            delay = min(delay * 2, retry_max_delay)

        finally:
            if pubsub is not None:
                with contextlib.suppress(Exception):
                    await pubsub.unsubscribe(ROBOT_CH, COMMON_CH)
                with contextlib.suppress(Exception):
                    await pubsub.close()
