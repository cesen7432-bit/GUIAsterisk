from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.schedule import Holiday, Schedule, ScheduleHours

router = APIRouter()


class HoursIn(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str


class HolidayIn(BaseModel):
    date: date
    description: str = ""


class ScheduleIn(BaseModel):
    name: str
    dest_open_type: str = ""
    dest_open_id: str = ""
    dest_closed_type: str = ""
    dest_closed_id: str = ""
    dest_holiday_type: str = ""
    dest_holiday_id: str = ""
    hours: List[HoursIn] = []
    holidays: List[HolidayIn] = []


@router.get("/")
async def list_schedules(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [{"id": s.id, "name": s.name} for s in db.query(Schedule).all()]


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "No encontrado")
    return {
        "id": s.id, "name": s.name,
        "dest_open_type": s.dest_open_type, "dest_open_id": s.dest_open_id,
        "dest_closed_type": s.dest_closed_type, "dest_closed_id": s.dest_closed_id,
        "dest_holiday_type": s.dest_holiday_type, "dest_holiday_id": s.dest_holiday_id,
        "hours": [{"day_of_week": h.day_of_week, "start_time": h.start_time, "end_time": h.end_time} for h in s.hours],
        "holidays": [{"date": str(h.date), "description": h.description} for h in s.holidays],
    }


@router.post("/", status_code=201)
async def create_schedule(body: ScheduleIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    s = Schedule(**{k: v for k, v in body.dict().items() if k not in ("hours", "holidays")})
    db.add(s)
    db.flush()
    for h in body.hours:
        db.add(ScheduleHours(schedule_id=s.id, **h.dict()))
    for hd in body.holidays:
        db.add(Holiday(schedule_id=s.id, **hd.dict()))
    db.commit()
    return {"id": s.id}


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: int, body: ScheduleIn,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "No encontrado")
    for k, v in body.dict(exclude={"hours", "holidays"}).items():
        setattr(s, k, v)
    for h in s.hours:
        db.delete(h)
    for hd in s.holidays:
        db.delete(hd)
    db.flush()
    for h in body.hours:
        db.add(ScheduleHours(schedule_id=s.id, **h.dict()))
    for hd in body.holidays:
        db.add(Holiday(schedule_id=s.id, **hd.dict()))
    db.commit()
    return {"ok": True}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "No encontrado")
    db.delete(s)
    db.commit()
    return {"ok": True}
