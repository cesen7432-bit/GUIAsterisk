from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    dest_open_type = Column(String(50), default="")
    dest_open_id = Column(String(50), default="")
    dest_closed_type = Column(String(50), default="")
    dest_closed_id = Column(String(50), default="")
    dest_holiday_type = Column(String(50), default="")
    dest_holiday_id = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    hours = relationship("ScheduleHours", back_populates="schedule", cascade="all, delete-orphan")
    holidays = relationship("Holiday", back_populates="schedule", cascade="all, delete-orphan")


class ScheduleHours(Base):
    __tablename__ = "schedule_hours"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)

    schedule = relationship("Schedule", back_populates="hours")


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String(200), default="")

    schedule = relationship("Schedule", back_populates="holidays")
