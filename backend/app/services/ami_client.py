import asyncio
import logging
from typing import Callable, Dict, List, Optional

from ..config import settings

logger = logging.getLogger(__name__)


class AMIClient:
    def __init__(self):
        self.host = settings.ami_host
        self.port = settings.ami_port
        self.username = settings.ami_user
        self.password = settings.ami_password
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._action_id = 0
        self._lock = asyncio.Lock()

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            greeting = await self.reader.readline()
            logger.info(f"AMI: {greeting.decode().strip()}")
            self.connected = True
            resp = await self._send_raw(
                {"Action": "Login", "Username": self.username, "Secret": self.password}
            )
            if resp and resp.get("Response") == "Success":
                logger.info("AMI authenticated")
                asyncio.create_task(self._listen())
            else:
                logger.error("AMI auth failed")
                self.connected = False
        except Exception as e:
            logger.error(f"AMI connect error: {e}")
            self.connected = False

    async def reconnect_loop(self):
        while True:
            if not self.connected:
                logger.info("AMI reconnecting...")
                await self.connect()
            await asyncio.sleep(10)

    def _next_id(self) -> str:
        self._action_id += 1
        return f"aid_{self._action_id}"

    async def _send_raw(self, action: Dict[str, str]) -> Optional[Dict]:
        aid = self._next_id()
        action["ActionID"] = aid
        msg = "".join(f"{k}: {v}\r\n" for k, v in action.items()) + "\r\n"

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._response_futures[aid] = future

        async with self._lock:
            self.writer.write(msg.encode())
            await self.writer.drain()

        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            self._response_futures.pop(aid, None)
            return None

    async def send_action(self, action: Dict[str, str]) -> Optional[Dict]:
        if not self.connected:
            return {"Response": "Error", "Message": "AMI not connected"}
        return await self._send_raw(action)

    async def _listen(self):
        buffer = ""
        while self.connected:
            try:
                line = await self.reader.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace")
                buffer += decoded
                if decoded == "\r\n":
                    msg = self._parse(buffer)
                    buffer = ""
                    await self._dispatch(msg)
            except Exception as e:
                logger.error(f"AMI listen error: {e}")
                self.connected = False
                break

    def _parse(self, raw: str) -> Dict:
        result = {}
        for line in raw.strip().split("\r\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                result[k.strip()] = v.strip()
        return result

    async def _dispatch(self, msg: Dict):
        aid = msg.get("ActionID")
        if aid and aid in self._response_futures:
            f = self._response_futures.pop(aid)
            if not f.done():
                f.set_result(msg)
            return

        event_type = msg.get("Event", "")
        for key in (event_type, "*"):
            for handler in self._event_handlers.get(key, []):
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error(f"AMI handler error: {e}")

    def on_event(self, event_type: str, handler: Callable):
        self._event_handlers.setdefault(event_type, []).append(handler)

    async def reload_module(self, module: str = ""):
        if module:
            return await self.send_action({"Action": "ModuleReload", "Module": module})
        return await self.send_action({"Action": "Reload"})

    async def hangup(self, channel: str):
        return await self.send_action({"Action": "Hangup", "Channel": channel})

    async def transfer(self, channel: str, exten: str, context: str):
        return await self.send_action(
            {"Action": "Redirect", "Channel": channel, "Exten": exten, "Context": context, "Priority": "1"}
        )

    async def originate(self, channel: str, exten: str, context: str, callerid: str = ""):
        action = {"Action": "Originate", "Channel": channel, "Exten": exten,
                  "Context": context, "Priority": "1", "Async": "true"}
        if callerid:
            action["CallerID"] = callerid
        return await self.send_action(action)

    async def queue_pause(self, interface: str, queue: str, paused: bool, reason: str = ""):
        action = {
            "Action": "QueuePause",
            "Interface": interface,
            "Queue": queue,
            "Paused": "true" if paused else "false",
        }
        if reason:
            action["Reason"] = reason
        return await self.send_action(action)

    async def spy(self, spy_channel: str, target_channel: str, mode: str = "q"):
        return await self.send_action({
            "Action": "Originate",
            "Channel": spy_channel,
            "Application": "ChanSpy",
            "Data": f"{target_channel},{mode}",
            "Async": "true",
        })

    async def get_active_channels(self) -> List[Dict]:
        resp = await self.send_action({"Action": "CoreShowChannels"})
        return []  # Events are received via the listener

    async def sip_show_peer(self, peer: str) -> Optional[Dict]:
        return await self.send_action({"Action": "SIPshowpeer", "Peer": peer})

    async def pjsip_show_endpoint(self, endpoint: str) -> Optional[Dict]:
        return await self.send_action({"Action": "PJSIPShowEndpoint", "Endpoint": endpoint})


ami_client = AMIClient()
