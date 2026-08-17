from functools import lru_cache

from pydantic import EmailStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = "development"
    app_secret: str = "development-only-secret"
    otp_pepper: str = "development-only-otp-pepper"

    # La aplicación construye la conexión a PostgreSQL con estas variables.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "imagen_report"
    postgres_user: str = "imagen_report"
    postgres_password: str = "change-me-local-only"

    # Solo los tests automatizados pueden sobrescribir la conexión con SQLite.
    database_url: str | None = None
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False

    bootstrap_admin_username: str = "admin"
    bootstrap_admin_email: EmailStr = "admin@example.com"
    bootstrap_admin_password: str = "change-me-now"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: EmailStr | None = None
    smtp_use_tls: bool = True

    google_sheets_service_account_file: str | None = None
    google_sheet_id: str = "1ATTcmm3rs4NjpBoD0113-Oht-YieQx-PdPk3b4SVJqU"
    google_sheet_range: str = "'Hoja 1'!A11:K"
    sheet_patient_name_header: str = "NOMBRE"
    sheet_patient_id_header: str = "CEDULA"
    sheet_doctor_header: str = "DR."
    sheet_recipient_email_header: str = "ENVIO A..."

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"

    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_refresh_token: str | None = None
    google_oauth_token_uri: str = "https://oauth2.googleapis.com/token"
    google_docs_template_id: str = "1K9VviEhFYcvEGruV5a3L8iBxnjX72J7c_8hB7rO99UE"
    google_drive_output_folder_id: str = "1OZXqOoi57mwh4hhYyBjECQ_5TgFfU1Ez"
    gmail_draft_enabled: bool = False
    gmail_user_id: str = "me"

    otp_ttl_minutes: int = Field(default=5, ge=1, le=30)
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    max_otp_attempts: int = Field(default=5, ge=1, le=10)

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "test"}

    @property
    def sqlalchemy_database_url(self) -> URL | str:
        if self.database_url:
            return self.database_url
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @model_validator(mode="after")
    def sqlite_is_test_only(self) -> "Settings":
        if (
            self.database_url
            and self.database_url.startswith("sqlite")
            and self.app_env.lower() != "test"
        ):
            raise ValueError("SQLite está permitido únicamente con APP_ENV=test.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
