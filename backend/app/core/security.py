import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

from app.core.config import Settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def new_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str, settings: Settings) -> str:
    return hmac.new(settings.otp_pepper.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp(code: str, expected_hash: str, settings: Settings) -> bool:
    return hmac.compare_digest(hash_otp(code, settings), expected_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def utcnow() -> datetime:
    return datetime.now(UTC)


def otp_expiry(settings: Settings) -> datetime:
    return utcnow() + timedelta(minutes=settings.otp_ttl_minutes)


def session_expiry(settings: Settings) -> datetime:
    return utcnow() + timedelta(hours=settings.session_ttl_hours)
