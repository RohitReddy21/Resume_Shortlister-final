from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    parsed_json = Column(Text, nullable=True)
    masked_candidate_id = Column(String, nullable=True, index=True)
    mask_policy = Column(Text, nullable=True)
    masked_pdf = Column(String, nullable=True)
    masked_docx = Column(String, nullable=True)
    masked_at = Column(DateTime(timezone=True), server_default=None, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    resume = relationship("Resume", back_populates="versions", foreign_keys=[resume_id])
