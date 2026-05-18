from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from ..database import Base


class Extension(Base):
    __tablename__ = "extensions"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    callerid = Column(String(100))
    password = Column(String(100), nullable=False)
    type = Column(Enum("sip", "webrtc"), default="sip")
    context = Column(String(50), default="from-internal")
    codecs = Column(String(200), default="ulaw,alaw")
    voicemail_enabled = Column(Boolean, default=False)
    recording = Column(Enum("never", "always", "ondemand"), default="never")
    followme_enabled = Column(Boolean, default=False)
    blacklist_enabled = Column(Boolean, default=False)
    language = Column(String(10), default="es")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
