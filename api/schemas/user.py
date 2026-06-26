import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.analyst


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class MeUpdate(BaseModel):
    language_pref: str | None = Field(None, pattern="^(fr|ar)$")
    full_name: str | None = Field(None, max_length=255)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    language_pref: str
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}
