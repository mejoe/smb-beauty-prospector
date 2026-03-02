import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Instagram auth (AES-256 encrypted at rest)
    ig_username: Mapped[str | None] = mapped_column(String(255))
    ig_session_cookie: Mapped[str | None] = mapped_column(Text)  # AES-256 encrypted JSON blob
    ig_session_valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ig_session_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # App settings
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free")

    # Relationships
    sessions: Mapped[list["ResearchSession"]] = relationship("ResearchSession", back_populates="user", cascade="all, delete-orphan")
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="user", cascade="all, delete-orphan")
    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    campaigns: Mapped[list["OutreachCampaign"]] = relationship("OutreachCampaign", back_populates="user", cascade="all, delete-orphan")
    enrichment_jobs: Mapped[list["EnrichmentJob"]] = relationship("EnrichmentJob", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
