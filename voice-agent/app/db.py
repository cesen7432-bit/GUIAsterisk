from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text, Time, create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

_url = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)
engine = create_engine(_url, pool_pre_ping=True, pool_size=10, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class VoiceTemplate(Base):
    __tablename__ = "voice_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    system_prompt = Column(Text)
    first_message = Column(Text)
    voice = Column(String(50), default="alloy")
    vad_threshold = Column(Float, default=0.6)


class VoiceCampaign(Base):
    __tablename__ = "voice_campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    template_id = Column(Integer)
    status = Column(String(20))
    max_concurrent = Column(Integer, default=4)
    schedule_start = Column(Time)
    schedule_end = Column(Time)
    max_retries = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=120)
    trunk = Column(String(50), default="openvox")


class VoiceContact(Base):
    __tablename__ = "voice_contacts"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer)
    phone = Column(String(30))
    variables = Column(JSON)
    status = Column(String(20))
    attempts = Column(Integer, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    updated_at = Column(DateTime)


class VoiceCallLog(Base):
    __tablename__ = "voice_call_logs"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer)
    channel_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    disposition = Column(String(50), nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)


@contextmanager
def get_session():
    s = SessionLocal()
    try:
        yield s
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
