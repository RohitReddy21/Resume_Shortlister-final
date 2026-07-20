from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(100), nullable=True)

    candidate_links = relationship("CandidateSkill", back_populates="skill")
    job_links = relationship("JobSkill", back_populates="skill")
