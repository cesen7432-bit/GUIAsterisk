import asyncio
from .config import settings


class PortPool:
    """Pool de puertos UDP para canales RTP."""

    def __init__(self):
        self._available: set[int] = set(
            range(settings.rtp_port_start, settings.rtp_port_end, 2)
        )
        self._lock = asyncio.Lock()

    async def acquire(self) -> int:
        async with self._lock:
            if not self._available:
                raise RuntimeError("Sin puertos RTP disponibles")
            return self._available.pop()

    async def release(self, port: int):
        async with self._lock:
            self._available.add(port)
