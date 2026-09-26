import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResearchStrategy(Base):
    """An admin-configured, named set of indicator parameters + AI-score
    weights/thresholds (see app/schemas/strategy.py::StrategyConfig for the
    shape stored in `config`). Rows are never deleted - "restore a previous
    configuration" is just reactivating an old row. Exactly one row is
    active at a time, enforced at the application layer (the activate
    endpoint deactivates every other row in the same transaction), not by a
    DB constraint."""

    __tablename__ = "research_strategies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
