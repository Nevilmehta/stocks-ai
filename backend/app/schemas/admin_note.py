import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class AdminNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message: str
    is_active: bool
    created_at: datetime.datetime


class AdminNoteCreateRequest(BaseModel):
    message: str
