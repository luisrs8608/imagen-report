import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import (
    hash_otp,
    hash_session_token,
    new_otp_code,
    new_session_token,
    otp_expiry,
    session_expiry,
    verify_otp,
    verify_password,
)
from app.models import AuthSession, OtpChallenge, User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, VerifyOtpRequest
from app.services.email_sender import send_otp_email
from app.services.errors import IntegrationNotConfigured

router = APIRouter(prefix="/auth", tags=["authentication"])


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'*' * max(2, len(local) - len(visible))}@{domain}"


def as_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username.strip()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    now = datetime.now(UTC)
    db.execute(
        update(OtpChallenge)
        .where(
            OtpChallenge.user_id == user.id,
            OtpChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    code = new_otp_code()
    challenge = OtpChallenge(
        id=uuid.uuid4().hex,
        user_id=user.id,
        code_hash=hash_otp(code, settings),
        expires_at=otp_expiry(settings),
    )
    db.add(challenge)
    db.commit()

    try:
        send_otp_email(user.email, code, settings)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return LoginResponse(
        challenge_id=challenge.id,
        masked_email=mask_email(user.email),
        expires_in_seconds=settings.otp_ttl_minutes * 60,
        development_code=code if settings.is_development else None,
    )


@router.post("/verify", response_model=UserResponse)
def verify_code(
    payload: VerifyOtpRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserResponse:
    challenge = db.get(OtpChallenge, payload.challenge_id)
    now = datetime.now(UTC)
    if not challenge or challenge.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now or challenge.attempts >= settings.max_otp_attempts:
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El código venció.")

    challenge.attempts += 1
    if not verify_otp(payload.code, challenge.code_hash, settings):
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código inválido.")

    challenge.consumed_at = now
    raw_token = new_session_token()
    session = AuthSession(
        id=uuid.uuid4().hex,
        user_id=challenge.user_id,
        token_hash=hash_session_token(raw_token),
        expires_at=session_expiry(settings),
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key="session_token",
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return as_user_response(session.user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return as_user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    if session_token:
        session = db.scalar(
            select(AuthSession).where(AuthSession.token_hash == hash_session_token(session_token))
        )
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            db.commit()
    response.delete_cookie("session_token", path="/")
