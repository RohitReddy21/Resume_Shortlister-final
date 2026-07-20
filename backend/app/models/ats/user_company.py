from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserCompany(Base):
    __tablename__ = "user_companies"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), primary_key=True)
    role = Column(String(50), nullable=False)

    user = relationship("User", back_populates="company_links")
    company = relationship("Company", back_populates="user_links")
