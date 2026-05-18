import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional

import httpx
import websockets

from ..config import settings

logger = logging.getLogger(__name__)


class ARIClient:
    def __init__(self):
        self.base_url = f"http://{settings.ari_host}:{settings.ari_port}/ari"
        self.ws_url = f"ws://{settings.ari_host}:{settings.ari_port}/ari/events"
        self.auth = (settings.ari_user, settings.ari_password)
        self._client: Optional[httpx.AsyncClient] = None
        self._event_handlers: List[Callable] = []
        self._ws_task: Optional[asyncio.Task] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(auth=self.auth, timeout=10.0)
        return self._client

    async def get(self, path: str, **params) -> Dict:
        r = await self.client.get(f"{self.base_url}{path}", params=params)
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, json_data: Optional[Dict] = None, **params) -> Dict:
        r = await self.client.post(
            f"{self.base_url}{path}", json=json_data, params=params
        )
        r.raise_for_status()
        return r.json() if r.content else {}

    async def delete(self, path: str, **params) -> None:
        r = await self.client.delete(f"{self.base_url}{path}", params=params)
        r.raise_for_status()

    async def put(self, path: str, json_data: Optional[Dict] = None) -> Dict:
        r = await self.client.put(f"{self.base_url}{path}", json=json_data)
        r.raise_for_status()
        return r.json() if r.content else {}

    async def get_info(self) -> Dict:
        return await self.get("/asterisk/info")

    async def get_channels(self) -> List[Dict]:
        return await self.get("/channels")

    async def get_channel(self, channel_id: str) -> Dict:
        return await self.get(f"/channels/{channel_id}")

    async def hangup_channel(self, channel_id: str, reason: str = "normal"):
        await self.delete(f"/channels/{channel_id}", reason=reason)

    async def get_bridges(self) -> List[Dict]:
        return await self.get("/bridges")

    async def get_endpoints(self) -> List[Dict]:
        return await self.get("/endpoints")

    async def get_endpoint(self, tech: str, resource: str) -> Dict:
        return await self.get(f"/endpoints/{tech}/{resource}")

    async def get_pjsip_endpoints(self) -> List[Dict]:
        try:
            return await self.get("/endpoints/PJSIP")
        except Exception:
            return []

    async def get_recordings(self) -> List[Dict]:
        return await self.get("/recordings/stored")

    async def delete_recording(self, name: str):
        await self.delete(f"/recordings/stored/{name}")

    async def get_applications(self) -> List[Dict]:
        return await self.get("/applications")

    async def start_ws(self, app_name: str = "gui_monitor"):
        self._ws_task = asyncio.create_task(self._ws_loop(app_name))

    async def _ws_loop(self, app_name: str):
        url = (
            f"{self.ws_url}"
            f"?api_key={settings.ari_user}:{settings.ari_password}"
            f"&app={app_name}&subscribeAll=true"
        )
        while True:
            try:
                async with websockets.connect(url) as ws:
                    logger.info("ARI WebSocket connected")
                    async for raw in ws:
                        event = json.loads(raw)
                        for handler in self._event_handlers:
                            try:
                                await handler(event)
                            except Exception as e:
                                logger.error(f"ARI handler error: {e}")
            except Exception as e:
                logger.warning(f"ARI WS error: {e} — reconnecting in 5s")
                await asyncio.sleep(5)

    def on_event(self, handler: Callable):
        self._event_handlers.append(handler)


ari_client = ARIClient()
