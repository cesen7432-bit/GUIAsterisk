from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
from ..database import Base


class ARIUser(Base):
    __tablename__ = "ari_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    password_format = Column(Enum("plain", "crypt"), default="plain")
    permissions = Column(Enum("read_only", "read_write"), default="read_write")
    stasis_apps = Column(Text, default="")
    cors_origins = Column(Text, default="*")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
