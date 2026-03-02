import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="instagram_dm")  # instagram_dm, email (future)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, active, paused, complete
    message_template: Mapped[str | None] = mapped_column(Text)  # supports {{name}}, {{company}}, etc.
    send_from_ig_user: Mapped[str | None] = mapped_column(String(100))

    # Throttle settings
    daily_send_limit: Mapped[int] = mapped_column(Integer, default=20)
    delay_min_seconds: Mapped[int] = mapped_column(Integer, default=45)
    delay_max_seconds: Mapped[int] = mapped_column(Integer, default=120)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    messages: Mapped[list["OutreachMessage"]] = relationship("OutreachMessage", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<OutreachCampaign {self.name}>"


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outreach_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    instagram_handle: Mapped[str] = mapped_column(String(100), nullable=False)
    rendered_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, sent, failed, replied, opted_out
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    ig_thread_id: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign: Mapped["OutreachCampaign"] = relationship("OutreachCampaign", back_populates="messages")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="outreach_messages")

    def __repr__(self) -> str:
        return f"<OutreachMessage to @{self.instagram_handle} [{self.status}]>"
