"""
Pydantic schemas for authentication and user registration/login.
Strictly prevents role injection during public registration.
"""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class RegisterRequest(BaseModel):
    """
    Public registration payload.
    Note: No `role` field is accepted here; new registrations ALWAYS receive `user` role.
    """

    name: str = Field(..., min_length=2, max_length=120, description="Full name of the user")
    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (minimum 8 characters)",
    )

    @validator("name")
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 non-whitespace characters.")
        return cleaned

    @validator("email")
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email address format.")
        return cleaned

    class Config:
        extra = "forbid"  # Reject any attempt to pass unexpected fields like `role="admin"`


class LoginRequest(BaseModel):
    """User login credentials."""

    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")

    @validator("email")
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Safe public representation of a User (never exposes hashed_password)."""

    id: int
    name: str
    email: str
    role: str
    is_active: bool = True
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT access token response returned on login and registration."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserRoleUpdateRequest(BaseModel):
    """Admin request payload for managing user role or active status."""

    role: Optional[str] = Field(None, description="Target role: 'user' or 'admin'")
    is_active: Optional[bool] = Field(None, description="Whether account is active")
    name: Optional[str] = Field(None, min_length=2, max_length=120)

    @validator("role")
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("user", "admin"):
            raise ValueError("Role must be either 'user' or 'admin'.")
        return v
