from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User


def test_password_plus_email_code_creates_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with test_session() as db:
        db.add(
            User(
                username="doctor",
                email="doctor@example.com",
                password_hash=hash_password("a-valid-test-password"),
                is_admin=False,
            )
        )
        db.commit()

    def override_db() -> Generator[Session, None, None]:
        with test_session() as db:
            yield db

    settings = Settings(
        app_env="test",
        otp_pepper="test-otp-pepper",
        database_url="sqlite://",
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={"username": "doctor", "password": "a-valid-test-password"},
            )
            assert login_response.status_code == 200
            challenge = login_response.json()
            assert challenge["development_code"]

            verify_response = client.post(
                "/api/auth/verify",
                json={
                    "challenge_id": challenge["challenge_id"],
                    "code": challenge["development_code"],
                },
            )
            assert verify_response.status_code == 200
            assert verify_response.json()["username"] == "doctor"

            me_response = client.get("/api/auth/me")
            assert me_response.status_code == 200
            assert me_response.json()["email"] == "doctor@example.com"
    finally:
        app.dependency_overrides.clear()
