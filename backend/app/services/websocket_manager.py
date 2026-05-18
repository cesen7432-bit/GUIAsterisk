import json
import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"WS connected ({len(self._connections)} total)")

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info(f"WS disconnected ({len(self._connections)} remaining)")

    async def broadcast(self, message: dict):
        data = json.dumps(message, default=str)
        dead: List[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_to(self, ws: WebSocket, message: dict):
        try:
            await ws.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"WS send error: {e}")


ws_manager = WebSocketManager()
