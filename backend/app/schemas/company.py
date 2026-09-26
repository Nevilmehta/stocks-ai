import uuid

from pydantic import BaseModel, ConfigDict


class CompanyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
