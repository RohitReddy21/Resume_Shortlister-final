from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_id = Column(String, ForeignKey("refresh_tokens.id"), nullable=True, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    device = Column(String(100), nullable=True)
    geo_location = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="sessions")
    refresh_token = relationship("RefreshToken")
