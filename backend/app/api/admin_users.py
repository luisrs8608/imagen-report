from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models import AuthSession, OtpChallenge, User
from app.schemas.admin import (
    AdminUserResponse,
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)

router = APIRouter(prefix="/admin/users", tags=["user administration"])


def as_admin_user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


def get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return user


def revoke_user_access(user_id: int, db: Session) -> None:
    now = datetime.now(UTC)
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(
        update(OtpChallenge)
        .where(OtpChallenge.user_id == user_id, OtpChallenge.consumed_at.is_(None))
        .values(consumed_at=now)
    )


@router.get("", response_model=list[AdminUserResponse])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    users = db.scalars(select(User).order_by(User.username.asc())).all()
    return [as_admin_user_response(user) for user in users]


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    username = payload.username.strip().lower()
    email = str(payload.email).strip().lower()
    existing = db.scalar(select(User).where((User.username == username) | (User.email == email)))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario o correo ya existe.",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario o correo ya existe.",
        ) from exc
    db.refresh(user)
    return as_admin_user_response(user)


@router.patch("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    user = get_user_or_404(user_id, db)
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes desactivar tu propio usuario.",
        )
    if user.id == admin.id and payload.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes quitarte tu propio rol de administrador.",
        )

    removes_active_admin = (
        user.is_admin
        and user.is_active
        and (payload.is_admin is False or payload.is_active is False)
    )
    if removes_active_admin:
        remaining_admins = db.scalar(
            select(func.count(User.id)).where(
                User.id != user.id,
                User.is_admin.is_(True),
                User.is_active.is_(True),
            )
        )
        if not remaining_admins:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Debe permanecer al menos un administrador activo.",
            )

    revoke_access = False
    if payload.email is not None:
        email = str(payload.email).strip().lower()
        duplicate = db.scalar(select(User).where(User.email == email, User.id != user.id))
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo ya está asignado a otro usuario.",
            )
        if email != user.email:
            user.email = email
    if payload.is_active is not None and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        revoke_access = revoke_access or not payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if revoke_access:
        revoke_user_access(user.id, db)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No fue posible guardar el usuario porque los datos ya existen.",
        ) from exc
    db.refresh(user)
    return as_admin_user_response(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = get_user_or_404(user_id, db)
    user.password_hash = hash_password(payload.password)
    revoke_user_access(user.id, db)
    db.commit()
