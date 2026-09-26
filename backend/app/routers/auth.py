from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.email_service import send_welcome_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookie(response: Response, user_id) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    _set_auth_cookie(response, user.id)
    return AuthResponse(user=UserPublic.model_validate(user))


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AuthResponse:
    if not settings.allow_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled. Ask an administrator to create your account.",
        )

    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=UserRole.user,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_welcome_email, user.display_name, user.email)

    _set_auth_cookie(response, user.id)
    return AuthResponse(user=UserPublic.model_validate(user))


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
