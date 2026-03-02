from pydantic import BaseModel
from datetime import datetime
from typing import Any
import uuid


class ContactCreate(BaseModel):
    company_id: uuid.UUID | None = None
    name: str
    role: str | None = None
    credentials: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    instagram_handle: str | None = None
    source: str | None = None
    crm_notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    credentials: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    instagram_handle: str | None = None
    status: str | None = None
    crm_notes: str | None = None
    tags: list[str] | None = None
    next_followup_at: datetime | None = None


class ContactResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None
    name: str
    role: str | None
    credentials: str | None
    email: str | None
    phone: str | None
    linkedin_url: str | None
    instagram_handle: str | None
    instagram_followers: int | None
    instagram_bio: str | None
    ig_confidence_score: Any | None
    ig_match_method: str | None
    enrichment_status: str
    status: str
    crm_notes: str | None
    tags: list | None
    last_contacted_at: datetime | None
    source: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
