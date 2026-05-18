from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from ..database import Base


class Trunk(Base):
    __tablename__ = "trunks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    password = Column(String(100))
    host = Column(String(200), nullable=False)
    port = Column(Integer, default=5060)
    codecs = Column(String(200), default="ulaw,alaw")
    context_in = Column(String(50), default="from-trunk")
    match_ip = Column(Boolean, default=False)
    nat_ip = Column(String(200), nullable=True)
    registration = Column(Enum("receive", "send", "none"), default="send")
    qualify_frequency = Column(Integer, default=60)
    direct_media = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
