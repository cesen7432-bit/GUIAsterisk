from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin, get_current_user
from ..database import get_db
from ..services.ami_client import ami_client
from ..services.ari_client import ari_client
from ..services.config_generator import generate_all
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/status")
async def system_status(_=Depends(get_current_user)):
    ami_ok = ami_client.connected
    ari_info = None
    try:
        ari_info = await ari_client.get_info()
    except Exception:
        pass
    return {
        "ami_connected": ami_ok,
        "ari_connected": ari_info is not None,
        "asterisk_info": ari_info,
    }


@router.post("/reload")
async def reload_asterisk(module: str = "", _=Depends(require_admin)):
    resp = await ami_client.reload_module(module)
    return resp or {"ok": True}


@router.post("/generate-configs")
async def generate_configs(db: Session = Depends(get_db), _=Depends(require_admin)):
    try:
        generate_all(db)
        return {"ok": True, "message": "Configuraciones generadas correctamente"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/active-calls")
async def active_calls(_=Depends(get_current_user)):
    try:
        channels = await ari_client.get_channels()
        return channels
    except Exception as e:
        return []


@router.get("/endpoints")
async def get_endpoints(_=Depends(get_current_user)):
    try:
        endpoints = await ari_client.get_pjsip_endpoints()
        return endpoints
    except Exception as e:
        return []
