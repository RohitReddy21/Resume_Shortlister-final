from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleOAuthRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.get("/google/login")
def google_login() -> RedirectResponse:
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google OAuth is not configured")

    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@router.post("/signup", response_model=TokenResponse)
def signup(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    _, tokens = AuthService.signup(db, payload)
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    _, tokens = AuthService.login(db, str(payload.email), payload.password)
    return tokens


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return AuthService.forgot_password(db, payload)


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return AuthService.reset_password(db, payload)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: dict[str, str], db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService.refresh_token(db, payload.get("refresh_token", ""))


@router.post("/logout")
def logout(payload: dict[str, str], db: Session = Depends(get_db)) -> dict[str, str]:
    return AuthService.logout(db, payload.get("refresh_token", ""))


@router.post("/google", response_model=TokenResponse)
def google_oauth(payload: GoogleOAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, tokens = AuthService.google_oauth(db, payload.code)
    return tokens


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    _, tokens = AuthService.google_oauth(db, code)
    redirect_target = f"{settings.frontend_url}/oauth/callback?code={code}&access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    return RedirectResponse(url=redirect_target)


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)) -> UserOut:
    return current_user
