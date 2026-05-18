from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from ..database import Base

DEST_TYPES = ("extension", "queue", "ivr", "voicemail", "hangup")


class InboundRoute(Base):
    __tablename__ = "inbound_routes"

    id = Column(Integer, primary_key=True, index=True)
    did = Column(String(50), default="")
    callerid = Column(String(50), default="")
    destination_type = Column(Enum(*DEST_TYPES), nullable=False)
    destination_id = Column(String(50), default="")
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OutboundRoute(Base):
    __tablename__ = "outbound_routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    pattern = Column(String(50), nullable=False)
    trunk_id = Column(Integer, ForeignKey("trunks.id"), nullable=False)
    prefix_add = Column(String(20), default="")
    prefix_remove = Column(Integer, default=0)
    recording = Column(Boolean, default=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
