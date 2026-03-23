from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=100)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str = "access"

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str
