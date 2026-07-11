"""Punto de entrada del voice-agent."""
import asyncio
import logging

from fastapi import FastAPI
import uvicorn

from .ari import ARIClient
from .port_pool import PortPool
from .worker import run_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Agent", docs_url="/docs")
ari = ARIClient()
port_pool = PortPool()


@app.on_event("startup")
async def startup():
    await ari.start()
    asyncio.create_task(run_worker(ari, port_pool))
    logger.info("Voice Agent arrancado")


@app.on_event("shutdown")
async def shutdown():
    await ari.stop()


@app.get("/health")
def health():
    from .worker import _active
    return {"status": "ok", "active_calls": len(_active)}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8100, log_level="info")
