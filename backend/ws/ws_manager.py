# app/ws/ws_manager.py
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import Dict, Set, Any, Optional, Tuple
from fastapi import WebSocket


class WSManager:
    """
    Менеджер WS-комнат с поддержкой адресной доставки:
      - connect(ws, warehouse_id) -> session_id
      - list_rooms()
      - disconnect(ws)
      - broadcast_json(warehouse_id, data)
      - broadcast_all_json(data)
      - unicast_json(warehouse_id, session_id, data)  # ✨ новое
    """

    def __init__(self):
        # room -> session_id -> WebSocket
        self.rooms: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
        # обратная карта для быстрого disconnect: ws -> (room, session_id)
        self._ws_index: Dict[WebSocket, Tuple[str, str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, warehouse_id: str) -> str:
        """
        Принимает соединение, регистрирует в комнате и возвращает session_id.
        Старые вызовы, которые не используют возвращаемое значение, остаются валидны.
        """
        await ws.accept()
        sid = uuid.uuid4().hex
        async with self._lock:
            self.rooms[warehouse_id][sid] = ws
            self._ws_index[ws] = (warehouse_id, sid)
            print(
                f"✅ WS connected: room={warehouse_id} size={len(self.rooms[warehouse_id])}",
                flush=True,
            )
        return sid  # ← можно игнорировать в старом коде

    async def list_rooms(self) -> list[str]:
        async with self._lock:
            return list(self.rooms.keys())

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            room_sid = self._ws_index.pop(ws, None)
            if room_sid:
                room_id, sid = room_sid
                self.rooms.get(room_id, {}).pop(sid, None)
                if not self.rooms.get(room_id):
                    self.rooms.pop(room_id, None)
                return
            # fallback: если индекса нет, вычистим из всех (на всякий случай)
            empty_rooms = []
            for room_id, members in self.rooms.items():
                sids_to_del = [sid for sid, sock in members.items() if sock is ws]
                for sid in sids_to_del:
                    members.pop(sid, None)
                if not members:
                    empty_rooms.append(room_id)
            for r in empty_rooms:
                self.rooms.pop(r, None)

    async def broadcast_json(self, warehouse_id: str, data: Dict[str, Any]) -> int:
        async with self._lock:
            members = dict(self.rooms.get(warehouse_id, {}))  # sid -> ws
        if not members:
            return 0

        dead: list[Tuple[str, WebSocket]] = []
        sent = 0
        for sid, ws in members.items():
            try:
                await ws.send_json(data)
                sent += 1
            except Exception:
                dead.append((sid, ws))

        if dead:
            async with self._lock:
                room = self.rooms.get(warehouse_id)
                if room is not None:
                    for sid, ws in dead:
                        room.pop(sid, None)
                        self._ws_index.pop(ws, None)
                    if not room:
                        self.rooms.pop(warehouse_id, None)
        return sent

    async def broadcast_all_json(self, data: Dict[str, Any]) -> int:
        async with self._lock:
            recipients = list(self._ws_index.keys())
        if not recipients:
            return 0

        dead: list[WebSocket] = []
        sent = 0
        for ws in recipients:
            try:
                await ws.send_json(data)
                sent += 1
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    room_sid = self._ws_index.pop(ws, None)
                    if room_sid:
                        room_id, sid = room_sid
                        self.rooms.get(room_id, {}).pop(sid, None)
                        if not self.rooms.get(room_id):
                            self.rooms.pop(room_id, None)
        return sent

    async def unicast_json(self, warehouse_id: str, session_id: str, data: Dict[str, Any]) -> bool:
        """
        ✨ Адресная отправка одному сокету в комнате склада.
        Возвращает True, если доставлено.
        """
        async with self._lock:
            ws = self.rooms.get(warehouse_id, {}).get(session_id)
        if not ws:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception:
            async with self._lock:
                # чистим умерший сокет
                self.rooms.get(warehouse_id, {}).pop(session_id, None)
                self._ws_index.pop(ws, None)
                if not self.rooms.get(warehouse_id):
                    self.rooms.pop(warehouse_id, None)
            return False


manager = WSManager()
