import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PeriodType(str, enum.Enum):
    annual = "annual"
    quarterly = "quarterly"


class CompanyFinancials(Base):
    """Raw financial statement figures (revenue, profit, cash flow, debt, ...)."""

    __tablename__ = "company_financials"
    __table_args__ = (
        UniqueConstraint("company_id", "period_type", "period_label", name="uq_financials_company_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    period_label: Mapped[str] = mapped_column(nullable=False)  # e.g. "FY2024" or "Q1FY2025"
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # chronological order within period_type, 0 = oldest

    revenue: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    net_profit: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    operating_profit: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    eps: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    operating_cash_flow: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    total_debt: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)


class FinancialRatios(Base):
    """Derived ratios per period, used by the analytics/scoring engine."""

    __tablename__ = "financial_ratios"
    __table_args__ = (
        UniqueConstraint("company_id", "period_type", "period_label", name="uq_ratios_company_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    period_label: Mapped[str] = mapped_column(nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    pe_ratio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    pb_ratio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    roe: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    roce: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    debt_to_equity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    revenue_growth: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    profit_growth: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    net_margin: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    market_cap: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
