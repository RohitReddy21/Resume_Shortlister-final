from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id = Column(String, ForeignKey("jobs.id"), primary_key=True)
    skill_id = Column(String, ForeignKey("skills.id"), primary_key=True)

    job = relationship("Job")
    skill = relationship("Skill", back_populates="job_links")
