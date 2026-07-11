"""
Puente bidireccional de audio: Asterisk RTP (UDP) ↔ OpenAI Realtime API (WebSocket).

Formato en ambas direcciones: G.711 µ-law (ulaw), 8 kHz, mono.
OpenAI Realtime acepta g711_ulaw nativamente → sin resampleo.
"""
import asyncio
import base64
import json
import logging
from typing import Optional

import aiohttp
import websockets

from . import rtp as rtp_utils
from .config import settings

logger = logging.getLogger(__name__)

_OPENAI_RT_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"
_CHUNK_BYTES = 160  # G.711 8 kHz, 20 ms = 160 bytes por paquete


class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_audio):
        self._on_audio = on_audio
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.remote_addr: Optional[tuple] = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        if self.remote_addr is None:
            self.remote_addr = addr  # aprendemos la dirección de Asterisk con el primer paquete
        payload = rtp_utils.parse(data)
        if payload:
            self._on_audio(payload)

    def send(self, payload: bytes, seq: int, ts: int):
        if self.transport and self.remote_addr:
            packet = rtp_utils.build(payload, seq, ts, pt=0)  # PT=0 PCMU
            self.transport.sendto(packet, self.remote_addr)


async def run_audio_bridge(
    local_port: int,
    system_prompt: str,
    first_message: str,
    voice: str,
    vad_threshold: float,
    hangup_event: asyncio.Event,
) -> tuple[str, dict]:
    """
    Corre el puente de audio hasta que `hangup_event` se active.
    Devuelve (transcript, summary_dict).
    """
    transcript_parts: list[str] = []
    rtp_seq = 0
    rtp_ts = 0
    out_buf = bytearray()

    # Cola para audio entrante de Asterisk → OpenAI
    audio_in_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=500)

    def on_asterisk_audio(payload: bytes):
        try:
            audio_in_queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass

    # Levantar socket UDP
    loop = asyncio.get_running_loop()
    protocol = RTPProtocol(on_asterisk_audio)
    udp_transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol,
        local_addr=("0.0.0.0", local_port),
    )

    try:
        # Conectar a OpenAI Realtime
        openai_ws = await websockets.connect(
            _OPENAI_RT_URL,
            additional_headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            ping_interval=20,
        )

        try:
            # Configurar sesión
            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "instructions": system_prompt,
                    "voice": voice,
                    "input_audio_format": "g711_ulaw",
                    "output_audio_format": "g711_ulaw",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": vad_threshold,
                        "silence_duration_ms": 700,
                        "prefix_padding_ms": 300,
                    },
                },
            }))

            # La IA habla primero
            await openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "instructions": (
                        f"Inicia la conversación diciendo EXACTAMENTE: {first_message}"
                    ),
                },
            }))

            # Tarea: leer audio de Asterisk y enviarlo a OpenAI
            async def send_to_openai():
                while True:
                    payload = await audio_in_queue.get()
                    b64 = base64.b64encode(payload).decode()
                    await openai_ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": b64,
                    }))

            # Tarea: leer respuestas de OpenAI y enviar audio a Asterisk
            async def recv_from_openai():
                nonlocal rtp_seq, rtp_ts, out_buf
                async for raw in openai_ws:
                    event = json.loads(raw)
                    etype = event.get("type", "")

                    if etype == "response.audio.delta":
                        chunk = base64.b64decode(event.get("delta", ""))
                        out_buf.extend(chunk)
                        # Enviar en paquetes de 160 bytes (20 ms)
                        while len(out_buf) >= _CHUNK_BYTES:
                            pkt = bytes(out_buf[:_CHUNK_BYTES])
                            out_buf = out_buf[_CHUNK_BYTES:]
                            protocol.send(pkt, rtp_seq, rtp_ts)
                            rtp_seq += 1
                            rtp_ts += 160  # 8 kHz, 20 ms = 160 muestras

                    elif etype == "input_audio_buffer.speech_started":
                        # Barge-in: vaciar buffer y cancelar respuesta en curso
                        out_buf.clear()
                        with asyncio.suppress(Exception):
                            await openai_ws.send(json.dumps({"type": "response.cancel"}))

                    elif etype == "conversation.item.input_audio_transcription.completed":
                        text = event.get("transcript", "").strip()
                        if text:
                            transcript_parts.append(f"Cliente: {text}")
                            logger.debug(f"[STT] {text}")

                    elif etype == "response.audio_transcript.done":
                        text = event.get("transcript", "").strip()
                        if text:
                            transcript_parts.append(f"IA: {text}")
                            logger.debug(f"[IA] {text}")

                    elif etype == "error":
                        logger.error(f"OpenAI Realtime error: {event.get('error')}")

            sender = asyncio.create_task(send_to_openai())
            receiver = asyncio.create_task(recv_from_openai())

            # Esperar a que cuelguen
            await hangup_event.wait()

        finally:
            sender.cancel()
            receiver.cancel()
            with asyncio.suppress(Exception):
                await openai_ws.close()

    finally:
        udp_transport.close()

    # Resumen post-llamada con gpt-4o-mini (Chat API, no Realtime)
    transcript_text = "\n".join(transcript_parts)
    summary = await _get_summary(transcript_text)
    return transcript_text, summary


async def _get_summary(transcript: str) -> dict:
    """Llama a Chat Completions para obtener un resumen estructurado."""
    if not transcript:
        return {"resultado": "completado", "resumen": "Sin transcripción"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "response_format": {"type": "json_object"},
                    "max_tokens": 250,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Analiza la transcripción de una llamada automática y responde "
                                "SOLO con JSON: "
                                '{"resultado":"completado|voicemail|rechazado","resumen":"1-2 oraciones",'
                                '"compromiso_pago":true|false,"callback_solicitado":true|false}'
                            ),
                        },
                        {"role": "user", "content": transcript},
                    ],
                },
            ) as r:
                data = await r.json()
                return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        logger.warning(f"Error obteniendo resumen: {e}")
        return {"resultado": "completado", "resumen": "Sin análisis disponible"}
