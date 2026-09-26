from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import ActiveStrategy, get_active_strategy, get_current_user, get_market_data_provider
from app.models.company import Company
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistItem
from app.providers.market_data import MarketDataProvider
from app.routers.stocks import get_stock_ai_score, get_stock_detail
from app.schemas.watchlist import WatchlistAddRequest, WatchlistItemOut

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"], dependencies=[Depends(get_current_user)])


def _get_or_create_watchlist(db: Session, user: User) -> Watchlist:
    watchlist = db.query(Watchlist).filter(Watchlist.user_id == user.id).first()
    if watchlist is None:
        watchlist = Watchlist(user_id=user.id, name="My Watchlist")
        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)
    return watchlist


def _enrich(symbol: str, added_at, provider: MarketDataProvider, active: ActiveStrategy) -> WatchlistItemOut | None:
    try:
        detail = get_stock_detail(symbol, provider)
    except HTTPException:
        return None

    try:
        score = get_stock_ai_score(symbol, provider, active)
    except HTTPException:
        score = None

    return WatchlistItemOut(
        id=detail.id,
        symbol=detail.symbol,
        name=detail.name,
        sector=detail.sector,
        added_at=added_at,
        latest_price=detail.latest_price,
        change_percent=detail.change_percent,
        ai_score=score.overall_score if score else None,
        ai_label=score.label if score else None,
        pe_ratio=detail.pe_ratio,
        roe=detail.roe,
    )


@router.get("", response_model=list[WatchlistItemOut])
def get_watchlist(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> list[WatchlistItemOut]:
    watchlist = _get_or_create_watchlist(db, user)
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.watchlist_id == watchlist.id)
        .order_by(WatchlistItem.added_at.desc())
        .all()
    )

    company_by_id = {c.id: c for c in db.query(Company).filter(Company.id.in_([i.company_id for i in items])).all()}

    results: list[WatchlistItemOut] = []
    for item in items:
        company = company_by_id.get(item.company_id)
        if company is None:
            continue
        enriched = _enrich(company.symbol, item.added_at, provider, active)
        if enriched:
            results.append(enriched)
    return results


@router.post("", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistAddRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> WatchlistItemOut:
    company = provider.get_company(payload.symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    watchlist = _get_or_create_watchlist(db, user)

    existing = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.watchlist_id == watchlist.id, WatchlistItem.company_id == company.id)
        .first()
    )
    if existing is None:
        existing = WatchlistItem(watchlist_id=watchlist.id, company_id=company.id)
        db.add(existing)
        db.commit()
        db.refresh(existing)

    enriched = _enrich(company.symbol, existing.added_at, provider, active)
    if enriched is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not load stock data")
    return enriched


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> None:
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    watchlist = _get_or_create_watchlist(db, user)
    db.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == watchlist.id, WatchlistItem.company_id == company.id
    ).delete()
    db.commit()
