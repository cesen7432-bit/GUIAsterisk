from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Queue(Base):
    __tablename__ = "queues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    strategy = Column(
        Enum("ringall", "roundrobin", "leastrecent", "fewestcalls", "random"),
        default="ringall",
    )
    agent_timeout = Column(Integer, default=30)
    retry = Column(Integer, default=5)
    wrapup_time = Column(Integer, default=5)
    max_callers = Column(Integer, default=0)
    music_on_hold = Column(String(50), default="default")
    announce_position = Column(Boolean, default=False)
    announce_hold_time = Column(Boolean, default=False)
    announce_frequency = Column(Integer, default=30)
    recording = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    members = relationship("QueueMember", back_populates="queue", cascade="all, delete-orphan")


class QueueMember(Base):
    __tablename__ = "queue_members"

    id = Column(Integer, primary_key=True, index=True)
    queue_id = Column(Integer, ForeignKey("queues.id"), nullable=False)
    extension = Column(String(20), nullable=False)
    penalty = Column(Integer, default=0)

    queue = relationship("Queue", back_populates="members")
