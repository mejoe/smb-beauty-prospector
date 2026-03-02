from pydantic import BaseModel
from datetime import datetime
import uuid


class SessionCreate(BaseModel):
    name: str
    description: str | None = None


class SessionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    search_config: dict | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    search_config: dict | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
