from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password, hash_session_token, verify_password
from app.main import app
from app.models import AuthSession, User


def admin_client(*, is_admin: bool = True):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    raw_token = "admin-test-session"
    with test_session() as db:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin-test-password"),
            is_admin=is_admin,
        )
        db.add(admin)
        db.flush()
        db.add(
            AuthSession(
                id="admin-session",
                user_id=admin.id,
                token_hash=hash_session_token(raw_token),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        db.commit()
        admin_id = admin.id

    def override_db() -> Generator[Session, None, None]:
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client.cookies.set("session_token", raw_token)
    return client, test_session, admin_id


def test_admin_can_create_update_and_reset_user():
    client, test_session, _ = admin_client()
    try:
        create_response = client.post(
            "/api/admin/users",
            json={
                "username": "doctor.uno",
                "email": "Doctor.Uno@example.com",
                "password": "initial-password-123",
                "is_admin": False,
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["username"] == "doctor.uno"
        assert created["email"] == "doctor.uno@example.com"
        assert created["is_active"] is True

        list_response = client.get("/api/admin/users")
        assert list_response.status_code == 200
        assert [user["username"] for user in list_response.json()] == ["admin", "doctor.uno"]

        update_response = client.patch(
            f"/api/admin/users/{created['id']}",
            json={"email": "doctor.nuevo@example.com", "is_admin": True},
        )
        assert update_response.status_code == 200
        assert update_response.json()["email"] == "doctor.nuevo@example.com"
        assert update_response.json()["is_admin"] is True

        reset_response = client.post(
            f"/api/admin/users/{created['id']}/reset-password",
            json={"password": "replacement-password-456"},
        )
        assert reset_response.status_code == 204
        with test_session() as db:
            user = db.scalar(select(User).where(User.id == created["id"]))
            assert user
            assert verify_password("replacement-password-456", user.password_hash)
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_non_admin_cannot_manage_users():
    client, _, _ = admin_client(is_admin=False)
    try:
        response = client.get("/api/admin/users")
        assert response.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_admin_cannot_disable_or_demote_self():
    client, _, admin_id = admin_client()
    try:
        disable_response = client.patch(f"/api/admin/users/{admin_id}", json={"is_active": False})
        demote_response = client.patch(f"/api/admin/users/{admin_id}", json={"is_admin": False})
        assert disable_response.status_code == 409
        assert demote_response.status_code == 409
    finally:
        client.close()
        app.dependency_overrides.clear()
