from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Voicemail(Base):
    __tablename__ = "voicemail_config"

    id = Column(Integer, primary_key=True, index=True)
    extension = Column(String(20), unique=True, nullable=False)
    password = Column(String(20), default="1234")
    email = Column(String(200), default="")
    attach_audio = Column(Boolean, default=True)
    delete_after_email = Column(Boolean, default=False)
    greeting_file = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
