from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class FollowMe(Base):
    __tablename__ = "followme"

    id = Column(Integer, primary_key=True, index=True)
    extension = Column(String(20), unique=True, nullable=False)
    is_active = Column(Boolean, default=False)
    initial_ring_time = Column(Integer, default=20)
    strategy = Column(Enum("sequential", "simultaneous"), default="sequential")
    music_on_hold = Column(String(50), default="default")
    confirm_calls = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    destinations = relationship(
        "FollowMeDestination", back_populates="followme", cascade="all, delete-orphan"
    )


class FollowMeDestination(Base):
    __tablename__ = "followme_destinations"

    id = Column(Integer, primary_key=True, index=True)
    followme_id = Column(Integer, ForeignKey("followme.id"), nullable=False)
    number = Column(String(50), nullable=False)
    timeout = Column(Integer, default=20)
    order = Column(Integer, default=1)

    followme = relationship("FollowMe", back_populates="destinations")
