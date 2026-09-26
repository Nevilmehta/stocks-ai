import uuid
from datetime import date as Date

from sqlalchemy import Date as SqlDate
from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("company_id", "date", name="uq_price_history_company_date"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    date: Mapped[Date] = mapped_column(SqlDate, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)
