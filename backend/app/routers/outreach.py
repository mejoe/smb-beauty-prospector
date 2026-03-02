from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.database import get_db
from app.models.outreach import OutreachCampaign, OutreachMessage
from app.models.contact import Contact
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/outreach", tags=["outreach"])


class CampaignCreate(BaseModel):
    name: str
    message_template: str
    platform: str = "instagram_dm"
    daily_send_limit: int = 20
    delay_min_seconds: int = 45
    delay_max_seconds: int = 120


class CampaignUpdate(BaseModel):
    name: str | None = None
    message_template: str | None = None
    status: str | None = None
    daily_send_limit: int | None = None
    delay_min_seconds: int | None = None
    delay_max_seconds: int | None = None


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    status: str
    message_template: str | None
    daily_send_limit: int
    delay_min_seconds: int
    delay_max_seconds: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AddContactsRequest(BaseModel):
    contact_ids: list[uuid.UUID]


def render_template(template: str, contact: Contact, company_name: str = "") -> str:
    """Render message template with contact variables."""
    first_name = contact.name.split()[0] if contact.name else ""
    return (
        template
        .replace("{{name}}", contact.name or "")
        .replace("{{first_name}}", first_name)
        .replace("{{company}}", company_name)
        .replace("{{city}}", "")  # TODO: join company.city
        .replace("{{role}}", contact.role or "")
        .replace("{{credential}}", contact.credentials or "")
    )


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OutreachCampaign)
        .where(OutreachCampaign.user_id == current_user.id)
        .order_by(OutreachCampaign.created_at.desc())
    )
    return result.scalars().all()


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    req: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = OutreachCampaign(
        user_id=current_user.id,
        name=req.name,
        message_template=req.message_template,
        platform=req.platform,
        daily_send_limit=min(req.daily_send_limit, 30),  # Hard cap at 30
        delay_min_seconds=max(req.delay_min_seconds, 30),  # Min 30s
        delay_max_seconds=req.delay_max_seconds,
    )
    db.add(campaign)
    await db.flush()
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    req: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OutreachCampaign).where(
            OutreachCampaign.id == campaign_id,
            OutreachCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    return campaign


@router.post("/campaigns/{campaign_id}/send", status_code=status.HTTP_202_ACCEPTED)
async def start_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ⚠️ CONFIRMATION GATE: This endpoint queues DM sends.
    In development, actual sends are NOT executed.
    A prominent UI confirmation modal must be shown before calling this endpoint.
    """
    result = await db.execute(
        select(OutreachCampaign).where(
            OutreachCampaign.id == campaign_id,
            OutreachCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "paused"):
        raise HTTPException(status_code=400, detail=f"Campaign cannot be started from status: {campaign.status}")

    campaign.status = "active"
    # TODO: Enqueue Celery DM send task
    # from app.tasks.outreach import send_instagram_dm_campaign
    # send_instagram_dm_campaign.delay(str(campaign_id), str(current_user.id))
    return {"message": "Campaign activated (sends NOT executed in development mode)", "campaign_id": str(campaign_id)}


@router.post("/campaigns/{campaign_id}/pause", status_code=status.HTTP_200_OK)
async def pause_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OutreachCampaign).where(
            OutreachCampaign.id == campaign_id,
            OutreachCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "paused"
    return {"message": "Campaign paused", "campaign_id": str(campaign_id)}


@router.get("/campaigns/{campaign_id}/messages")
async def get_campaign_messages(
    campaign_id: uuid.UUID,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.campaign_id == campaign_id)
        .order_by(OutreachMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "instagram_handle": m.instagram_handle,
            "status": m.status,
            "sent_at": m.sent_at,
            "error": m.error,
        }
        for m in messages
    ]
