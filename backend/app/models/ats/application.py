from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True, index=True)
    status = Column(
        String(50),
        nullable=False,
        default="Applied",
    )  # Applied|Screening|Shortlisted|Interview|Technical|HR|Offer|Hired|Rejected
    pipeline_order = Column(Integer, nullable=False, default=0)
    match_score = Column(Float, nullable=True)
    match_confidence = Column(Float, nullable=True)
    shortlist_reason = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    resume = relationship("Resume")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="application", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="application")
