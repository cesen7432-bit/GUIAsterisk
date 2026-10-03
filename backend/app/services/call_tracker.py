"""Traduce eventos AMI a estados de llamada legibles y los publica por WebSocket.

Estados emitidos (campo "state"):
  dialing      → se empezó a marcar al destino
  ringing      → el destino está timbrando
  answered     → el destino contestó
  rejected     → el destino cortó/rechazó mientras timbraba
  busy         → el destino estaba ocupado (no llegó a timbrar)
  no_answer    → timbró hasta agotar el tiempo sin contestar
  cancelled    → quien llamó colgó antes de que contestaran
  unavailable  → destino no registrado / apagado / sin ruta
  failed       → congestión u otro error
  voicemail    → la llamada entró al buzón de voz de Asterisk
  ended        → la llamada terminó (incluye "result" final, duración y causa)
"""
import logging
import time
from typing import Awaitable, Callable, Dict

from .websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# DialStatus de DialEnd → estado
DIAL_STATUS_MAP = {
    "ANSWER": "answered",
    "BUSY": "busy",
    "NOANSWER": "no_answer",
    "CANCEL": "cancelled",
    "CHANUNAVAIL": "unavailable",
    "CONGESTION": "failed",
}


class CallTracker:
    def __init__(self, publish: Callable[[dict], Awaitable[None]]):
        self._publish = publish
        self._calls: Dict[str, dict] = {}

    def active_calls(self) -> list:
        return [{k: v for k, v in c.items() if k != "dest_uniqueids"} for c in self._calls.values()]

    async def handle(self, ev: dict):
        etype = ev.get("Event", "")
        handler = {
            "DialBegin": self._dial_begin,
            "DialState": self._dial_state,
            "Newstate": self._newstate,
            "DialEnd": self._dial_end,
            "Newexten": self._newexten,
            "Hangup": self._hangup,
        }.get(etype)
        if handler:
            await handler(ev)

    async def _emit(self, call: dict, state: str, **extra):
        call["state"] = state
        call.update(extra)
        public = {k: v for k, v in call.items() if k != "dest_uniqueids"}
        await self._publish({"source": "call", "event": {**public, "ts": time.time()}})

    async def _dial_begin(self, ev: dict):
        linkedid = ev.get("Linkedid") or ev.get("Uniqueid")
        call = self._calls.get(linkedid)
        if not call:
            call = self._calls[linkedid] = {
                "call_id": linkedid,
                "from": ev.get("CallerIDNum", ""),
                "to": ev.get("Exten") or ev.get("DialString", ""),
                "channel": ev.get("Channel", ""),
                "started_at": time.time(),
                "answered_at": None,
                "result": None,
                "rang": False,
                "dest_uniqueids": [],
            }
        call["dest_uniqueids"].append(ev.get("DestUniqueid"))
        await self._emit(call, "dialing", dest_channel=ev.get("DestChannel", ""))

    async def _mark_ringing(self, linkedid: str):
        call = self._calls.get(linkedid)
        if call and not call["rang"] and call["answered_at"] is None:
            call["rang"] = True
            await self._emit(call, "ringing")

    async def _dial_state(self, ev: dict):
        if ev.get("DialStatus") == "RINGING":
            await self._mark_ringing(ev.get("Linkedid", ""))

    async def _newstate(self, ev: dict):
        call = self._calls.get(ev.get("Linkedid", ""))
        if call and ev.get("Uniqueid") in call["dest_uniqueids"] and ev.get("ChannelStateDesc") == "Ringing":
            await self._mark_ringing(call["call_id"])

    async def _dial_end(self, ev: dict):
        call = self._calls.get(ev.get("Linkedid", ""))
        if not call or call["answered_at"] is not None:
            return
        dial_status = ev.get("DialStatus", "")
        state = DIAL_STATUS_MAP.get(dial_status, "failed")
        # Si timbraba y terminó en BUSY/CHANUNAVAIL, el destino cortó activamente
        if state in ("busy", "unavailable") and call["rang"]:
            state = "rejected"
        if state == "answered":
            call["answered_at"] = time.time()
        call["result"] = state
        await self._emit(call, state, dial_status=dial_status)

    async def _newexten(self, ev: dict):
        if ev.get("Application") != "VoiceMail":
            return
        call = self._calls.get(ev.get("Linkedid", ""))
        if call and call["result"] != "voicemail":
            call["result"] = "voicemail"
            await self._emit(call, "voicemail")

    async def _hangup(self, ev: dict):
        # Solo cerramos cuando cuelga el canal que originó la llamada
        linkedid = ev.get("Linkedid", "")
        if ev.get("Uniqueid") != linkedid:
            return
        call = self._calls.pop(linkedid, None)
        if not call:
            return
        now = time.time()
        result = call["result"]
        if result == "answered":
            result = "completed"
        elif result is None:
            result = "cancelled"
        talk = int(now - call["answered_at"]) if call["answered_at"] else 0
        await self._emit(
            call, "ended",
            result=result,
            duration=int(now - call["started_at"]),
            talk_seconds=talk,
            cause=int(ev.get("Cause") or 0),
            cause_txt=ev.get("Cause-txt", ""),
        )


call_tracker = CallTracker(ws_manager.broadcast)
