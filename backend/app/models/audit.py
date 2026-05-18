from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from ..database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("gui_users.id"), nullable=True)
    user_email = Column(String(200), default="")
    action = Column(String(50), nullable=False)
    resource = Column(String(50), nullable=False)
    resource_id = Column(String(50), default="")
    details = Column(Text, default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, server_default=func.now())
