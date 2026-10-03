"""Cliente ARI (Asterisk REST Interface) — HTTP + WebSocket."""
import asyncio
import json
import logging
from typing import Optional

import aiohttp
import websockets

from .config import settings

logger = logging.getLogger(__name__)

# Segundos que Asterisk deja timbrar antes de abandonar la llamada saliente
ORIGINATE_TIMEOUT = 35


class EventRouter:
    """Distribuye eventos ARI a colas asyncio por channel_id."""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}

    def subscribe(self, channel_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues[channel_id] = q
        return q

    def unsubscribe(self, channel_id: str):
        self._queues.pop(channel_id, None)

    async def dispatch(self, event: dict):
        # Extraer channel id desde distintas posiciones según tipo de evento
        cid = None
        if "channel" in event:
            cid = event["channel"].get("id")
        if cid and cid in self._queues:
            try:
                self._queues[cid].put_nowait(event)
            except asyncio.QueueFull:
                pass


class ARIClient:
    def __init__(self):
        self._base = f"http://{settings.ari_host}:{settings.ari_port}/ari"
        self._auth = aiohttp.BasicAuth(settings.ari_user, settings.ari_password)
        self._session: Optional[aiohttp.ClientSession] = None
        self.event_router = EventRouter()

    async def start(self):
        self._session = aiohttp.ClientSession()
        asyncio.create_task(self._ws_loop())

    async def stop(self):
        if self._session:
            await self._session.close()

    async def _ws_loop(self):
        """Mantiene la conexión WebSocket ARI activa y despacha eventos."""
        uri = (
            f"ws://{settings.ari_host}:{settings.ari_port}/ari/events"
            f"?app={settings.ari_app}&api_key={settings.ari_user}:{settings.ari_password}"
        )
        while True:
            try:
                async with websockets.connect(uri, ping_interval=20) as ws:
                    logger.info("ARI WebSocket conectado")
                    async for raw in ws:
                        try:
                            event = json.loads(raw)
                            await self.event_router.dispatch(event)
                        except Exception as e:
                            logger.debug(f"Error despachando evento ARI: {e}")
            except Exception as e:
                logger.warning(f"ARI WebSocket desconectado: {e}. Reconectando en 5 s...")
                await asyncio.sleep(5)

    async def originate(self, phone: str, trunk: str) -> str:
        """Origina llamada saliente. Devuelve channel_id."""
        async with self._session.post(
            f"{self._base}/channels",
            auth=self._auth,
            params={
                "endpoint": f"PJSIP/{phone}@{trunk}",
                "app": settings.ari_app,
                "appArgs": "outbound",
                "callerId": "Empresa",
                "timeout": ORIGINATE_TIMEOUT,
            },
        ) as r:
            r.raise_for_status()
            data = await r.json()
            return data["id"]

    async def hangup(self, channel_id: str):
        try:
            async with self._session.delete(
                f"{self._base}/channels/{channel_id}", auth=self._auth
            ) as r:
                if r.status not in (200, 204, 404):
                    logger.warning(f"hangup {channel_id}: HTTP {r.status}")
        except Exception as e:
            logger.debug(f"hangup ignorado: {e}")

    async def create_external_media(self, rtp_port: int) -> dict:
        """Crea canal externalMedia que envía/recibe audio vía RTP UDP."""
        async with self._session.post(
            f"{self._base}/channels/externalMedia",
            auth=self._auth,
            params={
                "app": settings.ari_app,
                "external_host": f"{settings.agent_rtp_host}:{rtp_port}",
                "format": "ulaw",
                "encapsulation": "rtp",
                "transport": "udp",
                "direction": "both",
            },
        ) as r:
            r.raise_for_status()
            return await r.json()

    async def create_bridge(self) -> str:
        async with self._session.post(
            f"{self._base}/bridges",
            auth=self._auth,
            params={"type": "mixing,dtmf_events"},
        ) as r:
            r.raise_for_status()
            return (await r.json())["id"]

    async def add_to_bridge(self, bridge_id: str, *channel_ids: str):
        async with self._session.post(
            f"{self._base}/bridges/{bridge_id}/addChannel",
            auth=self._auth,
            params={"channel": ",".join(channel_ids)},
        ) as r:
            r.raise_for_status()

    async def destroy_bridge(self, bridge_id: str):
        try:
            async with self._session.delete(
                f"{self._base}/bridges/{bridge_id}", auth=self._auth
            ) as r:
                pass
        except Exception:
            pass
