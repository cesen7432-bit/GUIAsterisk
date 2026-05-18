from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from ..database import Base


class Sound(Base):
    __tablename__ = "sounds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    filename = Column(String(200), unique=True, nullable=False)
    duration = Column(Float, default=0.0)
    size = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
