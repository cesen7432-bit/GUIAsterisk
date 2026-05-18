from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..services.ami_client import ami_client
from ..services.ari_client import ari_client

router = APIRouter()


@router.get("/channels")
async def active_channels(_=Depends(get_current_user)):
    try:
        channels = await ari_client.get_channels()
        return {"channels": channels, "count": len(channels)}
    except Exception as e:
        return {"channels": [], "count": 0, "error": str(e)}


@router.get("/endpoints")
async def endpoint_states(_=Depends(get_current_user)):
    try:
        endpoints = await ari_client.get_pjsip_endpoints()
        return {"endpoints": endpoints}
    except Exception as e:
        return {"endpoints": [], "error": str(e)}


@router.post("/channels/{channel_id}/hangup")
async def hangup(channel_id: str, _=Depends(get_current_user)):
    try:
        await ari_client.hangup_channel(channel_id)
        return {"ok": True}
    except Exception as e:
        resp = await ami_client.hangup(channel_id)
        return resp or {"ok": True}


@router.post("/channels/{channel_id}/transfer")
async def transfer(channel_id: str, exten: str, context: str = "from-internal", _=Depends(get_current_user)):
    resp = await ami_client.transfer(channel_id, exten, context)
    return resp or {"ok": True}


@router.post("/originate")
async def originate(
    channel: str, exten: str, context: str = "from-internal",
    callerid: str = "", _=Depends(get_current_user)
):
    resp = await ami_client.originate(channel, exten, context, callerid)
    return resp or {"ok": True}
