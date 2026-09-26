import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    role: UserRole = UserRole.user


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None
    display_name: str | None = None
