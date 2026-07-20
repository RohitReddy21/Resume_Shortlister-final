from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class HiringManager(Base):
    __tablename__ = "hiring_managers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=True)

    department = relationship("Department", back_populates="hiring_managers")
    jobs = relationship("Job", back_populates="hiring_manager")
