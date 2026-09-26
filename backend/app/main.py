from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, auth, compare, health, research, screener, stocks, watchlist
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.market_data_provider == "real":
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="StockAI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(stocks.router)
app.include_router(research.router)
app.include_router(watchlist.router)
app.include_router(compare.router)
app.include_router(screener.router)
