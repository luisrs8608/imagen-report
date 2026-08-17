from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class LoginResponse(BaseModel):
    challenge_id: str
    masked_email: str
    expires_in_seconds: int
    development_code: str | None = None


class VerifyOtpRequest(BaseModel):
    challenge_id: str
    code: str = Field(pattern=r"^\d{6}$")


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_admin: bool
