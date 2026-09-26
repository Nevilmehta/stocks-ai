from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import ActiveStrategy, get_active_strategy, get_ai_provider, get_current_user, get_market_data_provider
from app.providers.ai_provider import AIProvider
from app.providers.market_data import MarketDataProvider
from app.routers.stocks import get_stock_history
from app.services.stock_context import build_stock_context
from app.schemas.compare import CompareAIResponse, CompareRequest, CompareResponse, CompareRow

router = APIRouter(prefix="/api/compare", tags=["compare"], dependencies=[Depends(get_current_user)])

MIN_SYMBOLS = 2
MAX_SYMBOLS = 3


def _validate_symbols(symbols: list[str]) -> list[str]:
    deduped = list(dict.fromkeys(s.upper() for s in symbols))
    if len(deduped) < MIN_SYMBOLS or len(deduped) > MAX_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Select between {MIN_SYMBOLS} and {MAX_SYMBOLS} companies to compare.",
        )
    return deduped


@router.post("", response_model=CompareResponse)
def compare_stocks(
    payload: CompareRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> CompareResponse:
    symbols = _validate_symbols(payload.symbols)

    rows: list[CompareRow] = []
    for symbol in symbols:
        context = build_stock_context(symbol, provider, active)
        if context is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Company '{symbol}' not found")

        d, s = context.detail, context.score
        history = get_stock_history(symbol, range="1Y", provider=provider)

        rows.append(
            CompareRow(
                symbol=d.symbol,
                name=d.name,
                sector=d.sector,
                latest_price=d.latest_price,
                change_percent=d.change_percent,
                market_cap=d.market_cap,
                pe_ratio=d.pe_ratio,
                pb_ratio=d.pb_ratio,
                roe=d.roe,
                roce=d.roce,
                debt_to_equity=d.debt_to_equity,
                revenue_growth=d.revenue_growth,
                profit_growth=d.profit_growth,
                ai_score=s.overall_score if s else None,
                ai_label=s.label if s else None,
                technical_momentum=s.subscores.technical_momentum if s else None,
                risk_label=s.risk_label if s else None,
                history=history,
            )
        )

    return CompareResponse(rows=rows)


@router.post("/ai", response_model=CompareAIResponse)
def compare_stocks_ai(
    payload: CompareRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    ai_provider: AIProvider = Depends(get_ai_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> CompareAIResponse:
    symbols = _validate_symbols(payload.symbols)

    contexts = []
    for symbol in symbols:
        context = build_stock_context(symbol, provider, active)
        if context is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Company '{symbol}' not found")
        contexts.append(context)

    text = ai_provider.compare_stocks(contexts)
    return CompareAIResponse(text=text)
