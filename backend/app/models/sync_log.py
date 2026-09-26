import enum
import uuid
from datetime import date as Date
from datetime import datetime, timezone

from sqlalchemy import Date as SqlDate
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncSource(str, enum.Enum):
    scheduled = "scheduled"
    manual_admin = "manual_admin"
    manual_upload = "manual_upload"


class SyncStatus(str, enum.Enum):
    success = "success"
    failure = "failure"


class MarketDataSyncLog(Base):
    """One row per sync attempt (scheduled job, admin-triggered manual sync, or
    admin file upload) - backs the admin dashboard's last-sync status, the
    auto-sync-failed warning banner, and the import history list."""

    __tablename__ = "market_data_sync_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trade_date: Mapped[Date] = mapped_column(SqlDate, nullable=False, index=True)
    source: Mapped[SyncSource] = mapped_column(Enum(SyncSource), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), nullable=False)
    rows_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
