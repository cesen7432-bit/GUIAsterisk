"""Utilidades mínimas para parsear y construir paquetes RTP."""
import struct


def parse(data: bytes) -> bytes:
    """Extrae el payload de un paquete RTP. Devuelve b'' si el paquete es inválido."""
    if len(data) < 12:
        return b""
    first = data[0]
    if (first >> 6) != 2:  # version check
        return b""
    csrc_count = first & 0x0F
    has_extension = (first >> 4) & 0x01
    has_padding = (first >> 5) & 0x01

    offset = 12 + csrc_count * 4
    if has_extension and len(data) > offset + 4:
        ext_len = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
        offset += 4 + ext_len * 4

    payload = data[offset:]
    if has_padding and payload:
        pad_len = payload[-1]
        payload = payload[:-pad_len]
    return payload


def build(payload: bytes, seq: int, ts: int, ssrc: int = 0xCAFEBABE, pt: int = 0) -> bytes:
    """Construye un paquete RTP mínimo.
    PT=0  → PCMU (G.711 µ-law, 8 kHz)
    PT=11 → L16  (PCM 16-bit, depende del codec negociado con Asterisk)
    """
    header = struct.pack(">BBHII", 0x80, pt & 0x7F, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
    return header + payload
