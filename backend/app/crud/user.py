import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.core.security import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, full_name: str, password: Optional[str], role: str, auth_provider: str = "local") -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name,
        password_hash=get_password_hash(password) if password else None,
        role=role,
        auth_provider=auth_provider,
        is_verified=auth_provider != "local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_refresh_token_record(db: Session, user_id: str, token: str, expires_at: datetime) -> RefreshToken:
    record = RefreshToken(id=str(uuid.uuid4()), token=token, user_id=user_id, expires_at=expires_at)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def revoke_refresh_tokens_for_user(db: Session, user_id: str) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
    db.commit()


def get_refresh_token_record(db: Session, token: str) -> Optional[RefreshToken]:
    return db.query(RefreshToken).filter(RefreshToken.token == token).first()


def revoke_refresh_token(db: Session, refresh_token: RefreshToken) -> None:
    refresh_token.revoked = True
    db.commit()
