from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class GUIUser(Base):
    __tablename__ = "gui_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(Enum("admin", "supervisor", "agent"), default="agent")
    extension = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    permissions = relationship(
        "UserPermission", back_populates="user", cascade="all, delete-orphan"
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("gui_users.id"), nullable=False)
    module = Column(String(50), nullable=False)
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)

    user = relationship("GUIUser", back_populates="permissions")
