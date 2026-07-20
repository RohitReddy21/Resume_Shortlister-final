from sqlalchemy import Column, String, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)
    hiring_manager_id = Column(String, ForeignKey("hiring_managers.id"), nullable=True)
    skills = Column(Text, nullable=True)  # JSON array stored as text
    locations = Column(Text, nullable=True)  # JSON array or comma-separated
    remote_type = Column(String(50), nullable=True)  # 'onsite'|'remote'|'hybrid'
    status = Column(String(50), nullable=False, default="draft")  # draft|published|closed
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)

    department = relationship("Department", back_populates="jobs")
    hiring_manager = relationship("HiringManager", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="job", cascade="all, delete-orphan")
