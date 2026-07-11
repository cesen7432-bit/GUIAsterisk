from sqlalchemy import Column, Integer, String, Text, Enum, JSON, DateTime, Float, ForeignKey, Time
from sqlalchemy.sql import func
from ..database import Base


class VoiceTemplate(Base):
    __tablename__ = "voice_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    system_prompt = Column(Text, nullable=False)
    first_message = Column(Text, nullable=False)
    voice = Column(String(50), default="alloy")
    vad_threshold = Column(Float, default=0.6)
    created_at = Column(DateTime, server_default=func.now())


class VoiceCampaign(Base):
    __tablename__ = "voice_campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    template_id = Column(Integer, ForeignKey("voice_templates.id"), nullable=False)
    status = Column(Enum("draft", "active", "paused", "finished"), default="draft")
    max_concurrent = Column(Integer, default=4)
    schedule_start = Column(Time, default="09:00:00")
    schedule_end = Column(Time, default="18:00:00")
    max_retries = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=120)
    trunk = Column(String(50), default="openvox")
    created_at = Column(DateTime, server_default=func.now())


class VoiceContact(Base):
    __tablename__ = "voice_contacts"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("voice_campaigns.id"), nullable=False)
    phone = Column(String(30), nullable=False)
    variables = Column(JSON, nullable=False, default=dict)
    status = Column(
        Enum("pending", "calling", "completed", "voicemail", "no_answer", "failed"),
        default="pending",
    )
    attempts = Column(Integer, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class VoiceCallLog(Base):
    __tablename__ = "voice_call_logs"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("voice_contacts.id"), nullable=False)
    channel_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    disposition = Column(String(50), nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
