from pydantic import BaseModel, EmailStr

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class AuthResponse(BaseModel):
    user: UserPublic
