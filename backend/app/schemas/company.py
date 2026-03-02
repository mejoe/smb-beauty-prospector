from pydantic import BaseModel
from datetime import datetime
from typing import Any
import uuid


class CompanyCreate(BaseModel):
    name: str
    city: str | None = None
    state: str | None = None
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    instagram_handle: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    session_id: uuid.UUID | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    state: str | None = None
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    instagram_handle: str | None = None
    linkedin_url: str | None = None
    status: str | None = None
    notes: str | None = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    city: str | None
    state: str | None
    category: str | None
    address: str | None
    phone: str | None
    website: str | None
    instagram_handle: str | None
    instagram_followers: int | None
    linkedin_url: str | None
    yelp_rating: Any | None
    yelp_review_count: int | None
    status: str
    source: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyDetailResponse(CompanyResponse):
    """Company detail including contact count."""
    contact_count: int = 0
    last_enriched_at: datetime | None = None
    google_place_id: str | None = None
    yelp_url: str | None = None


class CompanySearchRequest(BaseModel):
    session_id: uuid.UUID
    search_config: dict | None = None
