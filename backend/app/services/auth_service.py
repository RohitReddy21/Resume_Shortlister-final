import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.crud.user import (
    authenticate_user,
    create_refresh_token_record,
    create_user,
    get_refresh_token_record,
    get_user_by_email,
    get_user_by_id,
    revoke_refresh_token,
    revoke_refresh_tokens_for_user,
)
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, TokenResponse, UserRegister
from app.models.user import User
from app.services.email_service import EmailService

settings = get_settings()
logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def signup(db: Session, payload: UserRegister) -> tuple[User, TokenResponse]:
        existing = get_user_by_email(db, payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        role = payload.role or "Candidate"
        user = create_user(db, str(payload.email), payload.full_name, payload.password, role)
        return user, AuthService._issue_tokens(db, user)

    @staticmethod
    def login(db: Session, email: str, password: str) -> tuple[User, TokenResponse]:
        logger.info(f"Login attempt for email: {email}")
        user = authenticate_user(db, email, password)
        if not user:
            logger.warning(f"Authentication failed for email: {email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        logger.info(f"Authentication successful for user: {user.email} (id={user.id})")
        return user, AuthService._issue_tokens(db, user)

    @staticmethod
    def forgot_password(db: Session, payload: ForgotPasswordRequest) -> dict[str, str]:
        user = get_user_by_email(db, str(payload.email))
        if not user:
            return {"message": "If the account exists, a password reset email has been sent."}
        reset_token = create_access_token(subject=user.id, role=user.role)
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        EmailService.send_password_reset_email(str(payload.email), reset_link)
        return {"message": "If the account exists, a password reset email has been sent."}

    @staticmethod
    def reset_password(db: Session, payload: ResetPasswordRequest) -> dict[str, str]:
        try:
            decoded = decode_token(payload.token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token") from exc

        user = get_user_by_id(db, decoded.get("sub"))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user.password_hash = None if payload.new_password is None else AuthService._hash_password(payload.new_password)
        db.commit()
        return {"message": "Password updated successfully"}

    @staticmethod
    def refresh_token(db: Session, refresh_token: str) -> TokenResponse:
        record = get_refresh_token_record(db, refresh_token)
        if not record or record.revoked or record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid")

        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

        user = get_user_by_id(db, payload.get("sub"))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        revoke_refresh_token(db, record)
        return AuthService._issue_tokens(db, user)

    @staticmethod
    def logout(db: Session, refresh_token: str) -> dict[str, str]:
        record = get_refresh_token_record(db, refresh_token)
        if record:
            revoke_refresh_token(db, record)
        return {"message": "Logged out successfully"}

    @staticmethod
    def google_oauth(db: Session, code: str) -> tuple[User, TokenResponse]:
        if not settings.google_client_id or not settings.google_client_secret:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth is not configured")

        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to complete Google OAuth")

        userinfo_response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        userinfo_response.raise_for_status()
        profile = userinfo_response.json()

        existing = get_user_by_email(db, profile.get("email", ""))
        if existing:
            user = existing
        else:
            user = create_user(
                db,
                profile.get("email", f"oauth-{code}@example.com"),
                profile.get("name", "Google User"),
                None,
                "Candidate",
                auth_provider="google",
            )
        user.avatar_url = profile.get("picture")
        user.is_verified = True
        db.commit()
        return user, AuthService._issue_tokens(db, user)

    @staticmethod
    def _issue_tokens(db: Session, user: User) -> TokenResponse:
        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token = create_refresh_token(subject=user.id, role=user.role)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        create_refresh_token_record(db, user.id, refresh_token, expires_at)
        logger.info(f"Tokens issued for user: {user.email} (id={user.id})")
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    def _hash_password(password: str) -> str:
        from app.core.security import get_password_hash

        return get_password_hash(password)
