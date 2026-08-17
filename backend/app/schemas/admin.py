from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = None
    is_admin: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "UpdateUserRequest":
        if self.email is None and self.is_active is None and self.is_admin is None:
            raise ValueError("Debe indicarse al menos un cambio.")
        return self


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)
