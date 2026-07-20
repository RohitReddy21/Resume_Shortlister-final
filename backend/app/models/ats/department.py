from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)

    hiring_managers = relationship("HiringManager", back_populates="department")
    jobs = relationship("Job", back_populates="department")
