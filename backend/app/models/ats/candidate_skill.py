from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id = Column(String, ForeignKey("candidates.id"), primary_key=True)
    skill_id = Column(String, ForeignKey("skills.id"), primary_key=True)
    proficiency = Column(String(50), nullable=True)
    endorsement_count = Column(Integer, default=0, nullable=False)

    candidate = relationship("Candidate", back_populates="candidate_skills")
    skill = relationship("Skill", back_populates="candidate_links")
