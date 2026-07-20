from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)

    role = relationship("Role", overlaps="permissions,roles")
    permission = relationship("Permission", overlaps="permissions,roles")
