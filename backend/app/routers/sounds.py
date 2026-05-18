import os
import subprocess

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..config import settings
from ..database import get_db
from ..models.sound import Sound

router = APIRouter()
SOUNDS_PATH = settings.sounds_path


@router.get("/")
async def list_sounds(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [
        {"id": s.id, "name": s.name, "filename": s.filename,
         "duration": s.duration, "size": s.size, "created_at": s.created_at}
        for s in db.query(Sound).all()
    ]


@router.post("/upload", status_code=201)
async def upload_sound(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    os.makedirs(SOUNDS_PATH, exist_ok=True)
    original_name = file.filename
    base_name = os.path.splitext(original_name)[0]
    dest_wav = os.path.join(SOUNDS_PATH, f"{base_name}.wav")
    dest_ulaw = os.path.join(SOUNDS_PATH, f"{base_name}.ulaw")

    # Save uploaded file
    tmp_path = os.path.join(SOUNDS_PATH, f"_tmp_{original_name}")
    async with aiofiles.open(tmp_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Convert to Asterisk-compatible format (8kHz mono ulaw) via sox/ffmpeg
    try:
        subprocess.run(
            ["sox", tmp_path, "-r", "8000", "-c", "1", dest_wav],
            check=True, capture_output=True
        )
        subprocess.run(
            ["sox", dest_wav, "-t", "ul", dest_ulaw],
            check=True, capture_output=True
        )
    except Exception:
        # If sox fails, just keep the original
        os.rename(tmp_path, dest_wav)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    size = os.path.getsize(dest_wav) if os.path.exists(dest_wav) else len(content)
    sound = Sound(name=base_name, filename=f"{base_name}.wav", size=size)
    db.add(sound)
    db.commit()
    db.refresh(sound)
    return {"id": sound.id, "name": sound.name}


@router.get("/{sound_id}/download")
async def download_sound(sound_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    sound = db.query(Sound).filter(Sound.id == sound_id).first()
    if not sound:
        raise HTTPException(404, "No encontrado")
    path = os.path.join(SOUNDS_PATH, sound.filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(path, filename=sound.filename)


@router.delete("/{sound_id}")
async def delete_sound(sound_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    sound = db.query(Sound).filter(Sound.id == sound_id).first()
    if not sound:
        raise HTTPException(404, "No encontrado")
    path = os.path.join(SOUNDS_PATH, sound.filename)
    if os.path.exists(path):
        os.remove(path)
    db.delete(sound)
    db.commit()
    return {"ok": True}
