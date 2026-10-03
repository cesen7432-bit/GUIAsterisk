FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema: compilador, mariadb-dev, ffmpeg (para faster-whisper), wget
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libmariadb-dev ffmpeg wget \
    && rm -rf /var/lib/apt/lists/*

# ── Piper TTS binary ────────────────────────────────────────────────────────
# Descarga el binario precompilado para amd64
RUN wget -q "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz" \
    -O /tmp/piper.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /usr/local/bin --strip-components=1 piper/piper \
    && rm /tmp/piper.tar.gz

# ── Modelo Piper español ────────────────────────────────────────────────────
RUN mkdir -p /app/models \
    && wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx" \
         -O /app/models/es_ES-mls_10246-low.onnx \
    && wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/mls_10246/low/es_ES-mls_10246-low.onnx.json" \
         -O /app/models/es_ES-mls_10246-low.onnx.json

# ── Python deps ─────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-descargar modelo Whisper (se guarda en ~/.cache/huggingface) ─────────
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

COPY app/ ./app/

CMD ["python", "-m", "app.main"]
