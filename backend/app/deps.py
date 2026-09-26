import uuid
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.strategy import ResearchStrategy
from app.models.user import User, UserRole
from app.providers.ai_provider import AIProvider, GeminiAIProvider, GroqAIProvider, MockAIProvider
from app.providers.market_data import MarketDataProvider, MockMarketDataProvider, RealMarketDataProvider
from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG, StrategyConfig
from app.security import ACCESS_TOKEN_COOKIE_NAME, decode_access_token


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=ACCESS_TOKEN_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
    if not access_token:
        raise unauthorized

    payload = decode_access_token(access_token)
    if not payload or "sub" not in payload:
        raise unauthorized

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_market_data_provider(db: Session = Depends(get_db)) -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider == "mock":
        return MockMarketDataProvider(db)
    if settings.market_data_provider == "real":
        return RealMarketDataProvider(db)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Market data provider '{settings.market_data_provider}' is not implemented yet.",
    )


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "mock":
        return MockAIProvider()
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key or not settings.gemini_model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI_PROVIDER=gemini requires GEMINI_API_KEY and GEMINI_MODEL to be set.",
            )
        return GeminiAIProvider(api_key=settings.gemini_api_key, model_name=settings.gemini_model)
    if settings.ai_provider == "groq":
        if not settings.groq_api_key or not settings.groq_model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI_PROVIDER=groq requires GROQ_API_KEY and GROQ_MODEL to be set.",
            )
        return GroqAIProvider(api_key=settings.groq_api_key, model_name=settings.groq_model)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"AI provider '{settings.ai_provider}' is not implemented yet.",
    )


@dataclass
class ActiveStrategy:
    name: str
    config: StrategyConfig


def get_active_strategy(db: Session = Depends(get_db)) -> ActiveStrategy:
    row = db.query(ResearchStrategy).filter(ResearchStrategy.is_active.is_(True)).first()
    if row is None:
        return ActiveStrategy(name="Default", config=DEFAULT_STRATEGY_CONFIG)
    return ActiveStrategy(name=row.name, config=StrategyConfig(**row.config))
