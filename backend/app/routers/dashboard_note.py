from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.admin_note import AdminNote
from app.schemas.admin_note import AdminNoteOut

router = APIRouter(prefix="/api/dashboard-note", tags=["dashboard-note"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=AdminNoteOut | None)
def get_dashboard_note(db: Session = Depends(get_db)) -> AdminNote | None:
    """The admin's current editorial note for the customer Dashboard, or None
    if there isn't one active - an empty/whitespace-only message is treated
    the same as no note (POST /api/admin/dashboard-note with an empty message
    is how an admin clears it, see that endpoint's docstring)."""
    note = db.query(AdminNote).filter(AdminNote.is_active.is_(True)).order_by(AdminNote.created_at.desc()).first()
    if note is None or not note.message.strip():
        return None
    return note
