import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin, require_supervisor
from ..config import settings
from ..database import get_db

router = APIRouter()
REC_PATH = settings.recordings_path


def _scan_recordings():
    result = []
    if not os.path.exists(REC_PATH):
        return result
    for root, _, files in os.walk(REC_PATH):
        for fn in files:
            if fn.endswith((".wav", ".mp3", ".gsm")):
                fp = os.path.join(root, fn)
                stat = os.stat(fp)
                result.append({
                    "name": fn,
                    "path": fp,
                    "size": stat.st_size,
                    "created": stat.st_mtime,
                })
    result.sort(key=lambda x: x["created"], reverse=True)
    return result


@router.get("/")
async def list_recordings(
    src: str = "", limit: int = 100,
    _=Depends(require_supervisor)
):
    recs = _scan_recordings()
    if src:
        recs = [r for r in recs if src in r["name"]]
    return recs[:limit]


@router.get("/{filename}/download")
async def download_recording(filename: str, _=Depends(require_supervisor)):
    for root, _, files in os.walk(REC_PATH):
        if filename in files:
            return FileResponse(os.path.join(root, filename), filename=filename)
    raise HTTPException(404, "Grabación no encontrada")


@router.delete("/{filename}")
async def delete_recording(filename: str, _=Depends(require_admin)):
    for root, _, files in os.walk(REC_PATH):
        if filename in files:
            os.remove(os.path.join(root, filename))
            return {"ok": True}
    raise HTTPException(404, "Grabación no encontrada")
