"""
Puente local 100% gratuito: Asterisk RTP ↔ Whisper STT + Ollama LLM + Piper TTS.
Sin APIs externas, sin costos. Todo corre en el mismo servidor.

Flujo por turno:
  audio ulaw 8 kHz → VAD (webrtcvad) → Whisper STT → Ollama LLM → Piper TTS → ulaw 8 kHz
"""
import asyncio
import audioop
import json
import logging
import subprocess
from pathlib import Path

import aiohttp
import numpy as np
import webrtcvad
from faster_whisper import WhisperModel

from . import rtp as rtp_utils
from .config import settings

logger = logging.getLogger(__name__)

# ── Constantes audio ──────────────────────────────────────────────────────────
_VAD_RATE         = 16000
_VAD_FRAME_MS     = 30
_VAD_FRAME_BYTES  = _VAD_RATE * _VAD_FRAME_MS // 1000 * 2   # 960 bytes = 30 ms
_SILENCE_FRAMES   = 20    # 20 × 30 ms = 600 ms → fin de elocución
_MIN_SPEECH_FRAMES = 4    # mínimo 120 ms de voz antes de empezar a grabar
_MAX_BUF_SECS     = 20    # descartar audio si supera este límite
_RTP_CHUNK        = 160   # 20 ms de ulaw 8 kHz → 1 paquete RTP

# ── Modelos (se inicializan una sola vez) ─────────────────────────────────────
_whisper: WhisperModel | None = None
_piper_sample_rate: int | None = None


def _load_whisper() -> WhisperModel:
    global _whisper
    if _whisper is None:
        logger.info(f"Cargando Whisper '{settings.whisper_model}' en CPU...")
        _whisper = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        logger.info("Whisper listo")
    return _whisper


def _load_piper_rate() -> int:
    global _piper_sample_rate
    if _piper_sample_rate is None:
        cfg = Path(settings.piper_model_path + ".json")
        if cfg.exists():
            _piper_sample_rate = json.loads(cfg.read_text())["audio"]["sample_rate"]
        else:
            _piper_sample_rate = 22050  # valor típico para modelos es_ES
        logger.info(f"Piper sample rate: {_piper_sample_rate} Hz")
    return _piper_sample_rate


# ── STT ───────────────────────────────────────────────────────────────────────

def _transcribe(pcm_16k: bytes) -> str:
    """Transcribe PCM 16 kHz int16 a texto español (bloqueante)."""
    audio = np.frombuffer(pcm_16k, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = _load_whisper().transcribe(
        audio,
        language="es",
        beam_size=1,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    return " ".join(s.text.strip() for s in segments).strip()


# ── LLM ───────────────────────────────────────────────────────────────────────

async def _llm(messages: list[dict]) -> str:
    """Envía el historial a Ollama y devuelve la respuesta."""
    url = f"http://{settings.ollama_host}:11434/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "num_predict": 120,         # frases cortas para teléfono
            "stop": ["\n\n", "Cliente:", "Usuario:"],
        },
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload,
                          timeout=aiohttp.ClientTimeout(total=40)) as r:
            data = await r.json()
            return data["message"]["content"].strip()


# ── TTS ───────────────────────────────────────────────────────────────────────

def _synthesize(text: str) -> bytes:
    """Convierte texto a ulaw 8 kHz usando el binario Piper (bloqueante)."""
    result = subprocess.run(
        [
            settings.piper_binary,
            "--model", settings.piper_model_path,
            "--output-raw",
            "--sentence-silence", "0.2",
        ],
        input=text.encode(),
        capture_output=True,
        timeout=20,
    )
    if result.returncode != 0:
        logger.error(f"Piper falló: {result.stderr.decode()[:300]}")
        return b""

    # raw int16 PCM al sample rate del modelo → resamplear a 8 kHz → ulaw
    rate = _load_piper_rate()
    pcm_8k, _ = audioop.ratecv(result.stdout, 2, 1, rate, 8000, None)
    return audioop.lin2ulaw(pcm_8k, 2)


# ── RTP ───────────────────────────────────────────────────────────────────────

class _RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, q: asyncio.Queue):
        self._q = q
        self.transport: asyncio.DatagramTransport | None = None
        self.remote: tuple | None = None
        self._seq = 0
        self._ts  = 0

    def connection_made(self, t):
        self.transport = t

    def datagram_received(self, data: bytes, addr: tuple):
        if self.remote is None:
            self.remote = addr
        payload = rtp_utils.parse(data)
        if payload:
            try:
                self._q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def send(self, ulaw_chunk: bytes):
        if self.transport and self.remote:
            pkt = rtp_utils.build(ulaw_chunk, self._seq, self._ts, pt=0)
            self.transport.sendto(pkt, self.remote)
            self._seq = (self._seq + 1) & 0xFFFF
            self._ts  = (self._ts  + 160)   & 0xFFFFFFFF


async def _emit_audio(proto: _RTPProtocol, ulaw: bytes, stop: asyncio.Event):
    """Envía ulaw al ritmo RTP correcto (20 ms por paquete)."""
    SILENCE = b"\xff" * _RTP_CHUNK   # silencio en ulaw
    for i in range(0, len(ulaw), _RTP_CHUNK):
        if stop.is_set():
            return
        chunk = ulaw[i : i + _RTP_CHUNK]
        if len(chunk) < _RTP_CHUNK:
            chunk = chunk + SILENCE[len(chunk):]
        proto.send(chunk)
        await asyncio.sleep(0.020)


# ── Puente principal ──────────────────────────────────────────────────────────

async def run_audio_bridge(
    local_port:    int,
    system_prompt: str,
    first_message: str,
    voice:         str,          # no usado con Piper — conservado por compatibilidad
    vad_threshold: float,
    hangup_event:  asyncio.Event,
) -> tuple[str, dict]:
    """
    Ejecuta el puente hasta que `hangup_event` se active.
    Devuelve (transcript, summary).
    """
    loop = asyncio.get_running_loop()
    transcript: list[str] = []
    history:    list[dict] = [
        {
            "role": "system",
            "content": (
                system_prompt
                + "\n\nRECUERDA: Estás en una llamada telefónica. "
                  "Responde con frases cortas y naturales. "
                  "Una o dos oraciones como máximo por turno."
            ),
        }
    ]

    # Socket UDP
    audio_q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=2000)
    proto = _RTPProtocol(audio_q)
    udp_t, _ = await loop.create_datagram_endpoint(
        lambda: proto, local_addr=("0.0.0.0", local_port)
    )

    vad = webrtcvad.Vad(int(vad_threshold * 3))  # 0-3 (usamos 0-1 mapeado a 0-3)

    stop_tts   = asyncio.Event()
    is_talking = False

    # Estado VAD
    vad_buf   = bytearray()
    spk_buf   = bytearray()
    spk_cnt   = 0
    sil_cnt   = 0
    in_speech = False

    async def ai_respond(user_text: str):
        nonlocal is_talking
        logger.info(f"  Cliente: {user_text!r}")
        transcript.append(f"Cliente: {user_text}")
        history.append({"role": "user", "content": user_text})

        try:
            ai_text = await _llm(history)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            ai_text = "Disculpe, tuve un inconveniente. ¿Me puede repetir?"

        logger.info(f"  IA: {ai_text!r}")
        transcript.append(f"IA: {ai_text}")
        history.append({"role": "assistant", "content": ai_text})

        ulaw = await loop.run_in_executor(None, _synthesize, ai_text)
        if ulaw:
            is_talking = True
            stop_tts.clear()
            await _emit_audio(proto, ulaw, stop_tts)
            is_talking = False

    try:
        # Cargar modelos (puede tardar la primera vez)
        logger.info("Cargando modelos locales...")
        await loop.run_in_executor(None, _load_whisper)
        await loop.run_in_executor(None, _load_piper_rate)

        # Saludo inicial (IA habla primero)
        logger.info(f"  IA→: {first_message!r}")
        transcript.append(f"IA: {first_message}")
        history.append({"role": "assistant", "content": first_message})
        ulaw_hi = await loop.run_in_executor(None, _synthesize, first_message)
        if ulaw_hi:
            stop_tts.clear()
            await _emit_audio(proto, ulaw_hi, stop_tts)

        # ── Bucle principal ──────────────────────────────────────────────────
        while not hangup_event.is_set():
            try:
                payload = await asyncio.wait_for(audio_q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # Decodificar ulaw → PCM 16 kHz
            pcm8  = audioop.ulaw2lin(payload, 2)
            pcm16, _ = audioop.ratecv(pcm8, 2, 1, 8000, _VAD_RATE, None)
            vad_buf.extend(pcm16)

            # Procesar en frames de 30 ms
            while len(vad_buf) >= _VAD_FRAME_BYTES:
                frame    = bytes(vad_buf[:_VAD_FRAME_BYTES])
                vad_buf  = vad_buf[_VAD_FRAME_BYTES:]

                try:
                    is_speech = vad.is_speech(frame, _VAD_RATE)
                except Exception:
                    is_speech = False

                if is_speech:
                    spk_cnt += 1
                    sil_cnt  = 0
                    if is_talking and spk_cnt >= 3:
                        stop_tts.set()   # barge-in: el cliente interrumpe
                    if spk_cnt >= _MIN_SPEECH_FRAMES or in_speech:
                        in_speech = True
                        spk_buf.extend(frame)
                        # Evitar buffer infinito
                        limit = _MAX_BUF_SECS * _VAD_RATE * 2
                        if len(spk_buf) > limit:
                            spk_buf = spk_buf[-limit:]
                else:
                    spk_cnt = 0
                    if in_speech:
                        sil_cnt += 1
                        spk_buf.extend(frame)
                        if sil_cnt >= _SILENCE_FRAMES:
                            # ── Fin de elocución ─────────────────────────
                            utterance = bytes(spk_buf)
                            spk_buf.clear()
                            sil_cnt   = 0
                            in_speech = False

                            text = await loop.run_in_executor(None, _transcribe, utterance)
                            if text:
                                await ai_respond(text)

    finally:
        udp_t.close()

    full_transcript = "\n".join(transcript)
    summary = await _summary(full_transcript)
    return full_transcript, summary


# ── Resumen post-llamada ──────────────────────────────────────────────────────

async def _summary(transcript: str) -> dict:
    if not transcript:
        return {"resultado": "completado", "resumen": "Sin transcripción"}
    try:
        prompt = (
            "Analiza la transcripción de una llamada de gestión telefónica. "
            "Responde SOLO con JSON válido (sin texto extra):\n"
            '{"resultado":"completado|voicemail|rechazado",'
            '"resumen":"máx 2 oraciones",'
            '"compromiso_pago":true/false,'
            '"callback_solicitado":true/false}\n\n'
            f"Transcripción:\n{transcript}"
        )
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"http://{settings.ollama_host}:11434/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 200},
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                data = await r.json()
                return json.loads(data["response"])
    except Exception as e:
        logger.warning(f"Error resumen: {e}")
        return {"resultado": "completado", "resumen": "Sin análisis"}
