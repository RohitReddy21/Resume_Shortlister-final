from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String, primary_key=True, index=True)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    interview_type = Column(
        Enum(
            "HR Interview", "Technical Interview", "Manager Round", "Final Round", "Client Round",
            name="interview_type"
        ),
        nullable=True
    )
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=True)  # Changed from String to Integer for better handling
    duration_minutes_str = Column(String(50), nullable=True)  # Keep old field for backward compatibility
    time_zone = Column(String(100), nullable=True)
    meeting_link = Column(String(500), nullable=True)
    office_location = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)
    interviewer = Column(String(255), nullable=True)
    interviewer_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(
        Enum("Scheduled", "Completed", "Cancelled", "No Show", "Rescheduled", name="interview_status"),
        nullable=False,
        default="Scheduled"
    )
    rescheduled_from_id = Column(String, ForeignKey("interviews.id"), nullable=True)  # Link to previous interview if rescheduled
    notes = Column(Text, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    application = relationship("Application", back_populates="interviews")
    candidate = relationship("Candidate", back_populates="interviews")
    job = relationship("Job", back_populates="interviews")
    interviewer_user = relationship("User", foreign_keys=[interviewer_user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    rescheduled_from = relationship("Interview", remote_side=[id], foreign_keys=[rescheduled_from_id])
