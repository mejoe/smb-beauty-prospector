import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.types import JSONBCompat as JSONB
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(String(255), index=True)
    role: Mapped[str | None] = mapped_column(String(255))
    credentials: Mapped[str | None] = mapped_column(String(100))

    # Contact info
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    # LinkedIn
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    linkedin_headline: Mapped[str | None] = mapped_column(Text)
    linkedin_profile: Mapped[dict | None] = mapped_column(JSONB)

    # Instagram (KEY ENRICHMENT FIELD)
    instagram_handle: Mapped[str | None] = mapped_column(String(100), index=True)
    instagram_display_name: Mapped[str | None] = mapped_column(String(255))
    instagram_bio: Mapped[str | None] = mapped_column(Text)
    instagram_followers: Mapped[int | None] = mapped_column(Integer)
    instagram_is_private: Mapped[bool | None] = mapped_column(Boolean)
    instagram_profile: Mapped[dict | None] = mapped_column(JSONB)
    ig_confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2))  # 0.00-1.00
    ig_match_method: Mapped[str | None] = mapped_column(String(50))  # followers_scrape, name_search, manual

    # Enrichment state
    enrichment_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # CRM
    status: Mapped[str] = mapped_column(String(50), default="prospect", index=True)
    crm_notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSONB)  # array of tag strings
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contacts")
    company: Mapped["Company | None"] = relationship("Company", back_populates="contacts")
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship("OutreachMessage", back_populates="contact")

    def __repr__(self) -> str:
        return f"<Contact {self.name} ({self.role})>"
