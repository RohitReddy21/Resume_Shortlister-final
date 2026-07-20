from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="activity_logs")
    candidate = relationship("Candidate")
    job = relationship("Job")
    application = relationship("Application", back_populates="activity_logs")
