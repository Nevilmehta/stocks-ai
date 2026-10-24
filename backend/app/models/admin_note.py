import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminNote(Base):
    """A free-text note the admin writes to guide customers (e.g. "consider
    X, avoid Y"), shown on the customer Dashboard. Same pattern as
    ResearchStrategy: rows are never deleted - posting a new note deactivates
    the previous one in the same transaction, giving a free history/audit
    trail. Exactly one row is active (shown) at a time, enforced at the
    application layer, not a DB constraint. This is the platform operator's
    own editorial content, not AI-generated and not a mechanical indicator
    output - kept deliberately separate from app/analytics/signal.py."""

    __tablename__ = "admin_notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
