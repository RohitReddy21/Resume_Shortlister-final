from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(current_user=Depends(require_role("Admin")), db: Session = Depends(get_db)) -> dict[str, str]:
    return {"message": f"Admin {current_user.full_name} can manage users"}
