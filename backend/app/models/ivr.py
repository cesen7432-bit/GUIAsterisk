from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

DEST_TYPES = ("extension", "queue", "ivr", "voicemail", "hangup")


class IVR(Base):
    __tablename__ = "ivrs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    welcome_audio = Column(String(200), default="")
    timeout = Column(Integer, default=10)
    max_attempts = Column(Integer, default=3)
    invalid_action = Column(Enum("repeat", "hangup"), default="repeat")
    timeout_action = Column(Enum("repeat", "hangup"), default="repeat")
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    options = relationship("IVROption", back_populates="ivr", cascade="all, delete-orphan")


class IVROption(Base):
    __tablename__ = "ivr_options"

    id = Column(Integer, primary_key=True, index=True)
    ivr_id = Column(Integer, ForeignKey("ivrs.id"), nullable=False)
    key = Column(String(5), nullable=False)
    destination_type = Column(Enum(*DEST_TYPES), nullable=False)
    destination_id = Column(String(50), default="")

    ivr = relationship("IVR", back_populates="options")
