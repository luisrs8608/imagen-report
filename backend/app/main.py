from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.patients import router as patients_router
from app.api.reports import router as reports_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.report_models import REPORT_MODEL_OPTIONS
from app.core.security import hash_password
from app.models import User
from app.schemas.config import PublicConfigResponse


def bootstrap_admin() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == settings.bootstrap_admin_username))
        if existing:
            return
        db.add(
            User(
                username=settings.bootstrap_admin_username,
                email=str(settings.bootstrap_admin_email).lower(),
                password_hash=hash_password(settings.bootstrap_admin_password),
                is_admin=True,
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    yield


settings = get_settings()


def validate_production_settings() -> None:
    if settings.is_development:
        return
    insecure_values = {
        "APP_SECRET": settings.app_secret == "development-only-secret",
        "OTP_PEPPER": settings.otp_pepper == "development-only-otp-pepper",
        "BOOTSTRAP_ADMIN_PASSWORD": settings.bootstrap_admin_password == "change-me-now",
        "POSTGRES_PASSWORD": settings.postgres_password == "change-me-local-only",
        "COOKIE_SECURE": not settings.cookie_secure,
    }
    invalid = [name for name, is_invalid in insecure_values.items() if is_invalid]
    if invalid:
        raise RuntimeError(
            "La configuración de producción contiene valores inseguros: " + ", ".join(invalid)
        )


validate_production_settings()
app = FastAPI(
    title="Imagen Report API",
    version="0.1.0",
    docs_url="/api/docs" if settings.is_development else None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", response_model=PublicConfigResponse, tags=["system"])
def public_config() -> PublicConfigResponse:
    return PublicConfigResponse(
        gmail_draft_enabled=settings.gmail_draft_enabled,
        report_default_model=settings.report_model,
        report_models=list(REPORT_MODEL_OPTIONS),
    )


app.include_router(auth_router, prefix="/api")
app.include_router(admin_users_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
