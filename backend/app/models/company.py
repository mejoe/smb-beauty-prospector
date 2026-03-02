import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.types import JSONBCompat as JSONB
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("research_sessions.id"), index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(String(255), index=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    state: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(100), index=True)  # medspa, plastic_surgery, dermatology, functional_med, weightloss

    # Contact info
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(Text)
    website_domain: Mapped[str | None] = mapped_column(String(255))

    # Social
    instagram_handle: Mapped[str | None] = mapped_column(String(100), index=True)
    instagram_followers: Mapped[int | None] = mapped_column(Integer)
    instagram_bio: Mapped[str | None] = mapped_column(Text)
    instagram_profile: Mapped[dict | None] = mapped_column(JSONB)
    linkedin_url: Mapped[str | None] = mapped_column(Text)

    # Discovery metadata
    yelp_url: Mapped[str | None] = mapped_column(Text)
    yelp_review_count: Mapped[int | None] = mapped_column(Integer)
    yelp_rating: Mapped[float | None] = mapped_column(Numeric(2, 1))
    google_place_id: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(100))  # google_places, yelp, serp, instagram_hashtag

    # CRM
    status: Mapped[str] = mapped_column(String(50), default="prospect", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="companies")
    session: Mapped["ResearchSession | None"] = relationship("ResearchSession", back_populates="companies")
    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company {self.name} ({self.city})>"
