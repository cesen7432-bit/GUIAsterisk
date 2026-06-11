import asyncio
import contextlib
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import Base, engine
from .routers import ari, auth, blacklist, cdr, extensions, followme, ivr
from .routers import monitor, queues, recordings, routes, schedules, sounds
from .routers import system, users, voicemail
from .routers import trunks
from .services.ami_client import ami_client
from .services.ari_client import ari_client
from .services.websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


def _run_migrations():
    migrations = [
        "ALTER TABLE trunks ADD COLUMN nat_ip VARCHAR(200) NULL",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            with contextlib.suppress(Exception):
                conn.execute(text(sql))
                conn.commit()


_run_migrations()


def _seed_admin():
    from .auth import get_password_hash
    from .config import settings
    from .database import SessionLocal
    from .models.user import GUIUser
    db = SessionLocal()
    try:
        if not db.query(GUIUser).filter(GUIUser.role == "admin").first():
            db.add(GUIUser(
                name="Admin",
                email=settings.admin_email,
                password_hash=get_password_hash(settings.admin_password),
                role="admin",
                is_active=True,
            ))
            db.commit()
            logger.info(f"Admin creado: {settings.admin_email}")
    finally:
        db.close()


_seed_admin()


def _init_asterisk_conf():
    import os
    from .config import settings
    path = os.path.join(settings.asterisk_config_path, "asterisk.conf")
    if os.path.exists(path):
        return
    content = """; asterisk.conf — creado automáticamente por Asterisk GUI Manager

[directories]
astetcdir => /etc/asterisk
astmoddir => /usr/lib/asterisk/modules
astvarlibdir => /var/lib/asterisk
astdbdir => /var/lib/asterisk
astkeydir => /var/lib/asterisk
astdatadir => /var/lib/asterisk
astagidir => /var/lib/asterisk/agi-bin
astspooldir => /var/spool/asterisk
astrundir => /var/run/asterisk
astlogdir => /var/log/asterisk

[options]
verbose = 3
debug = 0
nocolor = yes
"""
    with open(path, "w") as f:
        f.write(content)
    logger.info("asterisk.conf creado")


_init_asterisk_conf()

app = FastAPI(title="Asterisk GUI Manager", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",        tags=["auth"])
app.include_router(extensions.router,  prefix="/api/extensions",  tags=["extensions"])
app.include_router(trunks.router,      prefix="/api/trunks",      tags=["trunks"])
app.include_router(routes.router,      prefix="/api/routes",      tags=["routes"])
app.include_router(ivr.router,         prefix="/api/ivr",         tags=["ivr"])
app.include_router(followme.router,    prefix="/api/followme",    tags=["followme"])
app.include_router(queues.router,      prefix="/api/queues",      tags=["queues"])
app.include_router(cdr.router,         prefix="/api/cdr",         tags=["cdr"])
app.include_router(recordings.router,  prefix="/api/recordings",  tags=["recordings"])
app.include_router(blacklist.router,   prefix="/api/blacklist",   tags=["blacklist"])
app.include_router(voicemail.router,   prefix="/api/voicemail",   tags=["voicemail"])
app.include_router(schedules.router,   prefix="/api/schedules",   tags=["schedules"])
app.include_router(sounds.router,      prefix="/api/sounds",      tags=["sounds"])
app.include_router(system.router,      prefix="/api/system",      tags=["system"])
app.include_router(users.router,       prefix="/api/users",       tags=["users"])
app.include_router(ari.router,         prefix="/api/ari",         tags=["ari"])
app.include_router(monitor.router,     prefix="/api/monitor",     tags=["monitor"])


@app.on_event("startup")
async def startup():
    asyncio.create_task(_ami_loop())
    asyncio.create_task(ari_client.start_ws("gui_monitor"))

    async def ari_to_ws(event):
        await ws_manager.broadcast({"source": "ari", "event": event})

    ari_client.on_event(ari_to_ws)


async def _ami_loop():
    await ami_client.connect()

    async def ami_to_ws(event):
        await ws_manager.broadcast({"source": "ami", "event": event})

    ami_client.on_event("*", ami_to_ws)

    while True:
        if not ami_client.connected:
            logger.info("AMI reconnecting...")
            await ami_client.connect()
        await asyncio.sleep(10)


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/api/health")
async def health():
    return {"status": "ok", "ami": ami_client.connected}
