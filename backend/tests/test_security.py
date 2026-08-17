from app.core.config import Settings
from app.core.security import hash_otp, hash_password, verify_otp, verify_password


def test_password_hash_round_trip():
    encoded = hash_password("a-long-development-password")
    assert verify_password("a-long-development-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_otp_hash_uses_server_pepper():
    settings = Settings(otp_pepper="unit-test-pepper")
    encoded = hash_otp("123456", settings)
    assert verify_otp("123456", encoded, settings)
    assert not verify_otp("654321", encoded, settings)
