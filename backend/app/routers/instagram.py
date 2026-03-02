"""
Instagram router - Sprint 5: Session management + enrichment queue
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import uuid

from app.database import get_db
from app.models.user import User
from app.models.contact import Contact
from app.models.enrichment import EnrichmentJob
from app.dependencies import get_current_user
from app.services.encryption import encrypt, decrypt

router = APIRouter(prefix="/instagram", tags=["instagram"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class IGSessionRequest(BaseModel):
    username: str
    cookies_json: str  # JSON string of session cookies captured from browser


class IGSessionStatus(BaseModel):
    connected: bool
    username: str | None = None
    valid_at: datetime | None = None
    expires_at: datetime | None = None
    health: str = "unknown"  # ok, expired, missing


class BulkEnrichRequest(BaseModel):
    contact_ids: list[uuid.UUID]


# ─── Session Management ────────────────────────────────────────────────────────

@router.get("/session-status", response_model=IGSessionStatus)
async def get_session_status(
    current_user: User = Depends(get_current_user),
):
    """Get current Instagram session status."""
    if not current_user.ig_session_cookie:
        return IGSessionStatus(connected=False, health="missing")

    # Check expiry
    now = datetime.now(timezone.utc)
    expires = current_user.ig_session_expires_at
    # Make expires timezone-aware if needed (SQLite stores naive datetimes)
    if expires and expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)
    health = "ok"
    if expires and expires < now:
        health = "expired"

    return IGSessionStatus(
        connected=True,
        username=current_user.ig_username,
        valid_at=current_user.ig_session_valid_at,
        expires_at=expires,
        health=health,
    )


@router.get("/session/health")
async def session_health_check(
    current_user: User = Depends(get_current_user),
):
    """
    Verify Instagram session is still valid.

    STUB: Checks stored session expiry date.
    Real implementation would use Playwright to make a test request to
    instagram.com/accounts/edit/ and verify it doesn't redirect to login.

    TODO: Set up Playwright-based session validation.
    """
    if not current_user.ig_session_cookie:
        return {"valid": False, "reason": "no_session"}

    now = datetime.now(timezone.utc)
    expires = current_user.ig_session_expires_at
    # Make timezone-aware if needed (SQLite stores naive datetimes)
    if expires and expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)
    if expires and expires < now:
        return {
            "valid": False,
            "reason": "expired",
            "expired_at": expires.isoformat(),
        }

    return {
        "valid": True,
        "username": current_user.ig_username,
        "valid_at": current_user.ig_session_valid_at.isoformat() if current_user.ig_session_valid_at else None,
        "expires_at": expires.isoformat() if expires else None,
        "rate_limit_info": {
            "max_profile_views_per_hour": 50,
            "min_delay_seconds": 2,
            "max_delay_seconds": 5,
        },
    }


@router.post("/session", response_model=IGSessionStatus)
async def save_session(
    req: IGSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save Instagram session cookies (AES-256 encrypted at rest)."""
    encrypted = encrypt(req.cookies_json)
    now = datetime.now(timezone.utc)
    current_user.ig_username = req.username
    current_user.ig_session_cookie = encrypted
    current_user.ig_session_valid_at = now
    # Conservative 30-day expiry (Instagram sessions typically last ~90 days)
    current_user.ig_session_expires_at = now + timedelta(days=30)
    return IGSessionStatus(
        connected=True,
        username=current_user.ig_username,
        valid_at=current_user.ig_session_valid_at,
        expires_at=current_user.ig_session_expires_at,
        health="ok",
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Instagram account."""
    current_user.ig_username = None
    current_user.ig_session_cookie = None
    current_user.ig_session_valid_at = None
    current_user.ig_session_expires_at = None


# ─── Enrichment Queue ─────────────────────────────────────────────────────────

@router.get("/queue")
async def get_enrichment_queue(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List enrichment jobs for the current user.
    Joins with contact data to show name and company.
    """
    conditions = [
        EnrichmentJob.user_id == current_user.id,
        EnrichmentJob.entity_type == "contact",
    ]
    if status_filter:
        conditions.append(EnrichmentJob.status == status_filter)

    result = await db.execute(
        select(EnrichmentJob)
        .where(and_(*conditions))
        .order_by(EnrichmentJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    # Batch-load contact names
    contact_ids = [j.entity_id for j in jobs if j.entity_id]
    contact_map: dict[uuid.UUID, Contact] = {}
    if contact_ids:
        cr = await db.execute(
            select(Contact).where(Contact.id.in_(contact_ids))
        )
        for c in cr.scalars().all():
            contact_map[c.id] = c

    return [
        {
            "id": str(j.id),
            "entity_id": str(j.entity_id),
            "contact_name": contact_map[j.entity_id].name if j.entity_id in contact_map else None,
            "contact_ig": contact_map[j.entity_id].instagram_handle if j.entity_id in contact_map else None,
            "ig_confidence_score": float(contact_map[j.entity_id].ig_confidence_score) if j.entity_id in contact_map and contact_map[j.entity_id].ig_confidence_score else None,
            "ig_match_method": contact_map[j.entity_id].ig_match_method if j.entity_id in contact_map else None,
            "job_type": j.job_type,
            "status": j.status,
            "error": j.error,
            "result": j.result,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]


@router.post("/enrich/{contact_id}", status_code=status.HTTP_202_ACCEPTED)
async def enrich_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue Instagram enrichment for a single contact."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    job = EnrichmentJob(
        user_id=current_user.id,
        entity_type="contact",
        entity_id=contact_id,
        job_type="ig_enrichment",
        status="queued",
    )
    db.add(job)
    await db.flush()

    try:
        from app.tasks.enrichment import enrich_contact_instagram
        task = enrich_contact_instagram.delay(str(contact_id), str(current_user.id))
        job.celery_task_id = task.id
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning(f"Celery unavailable: {exc}")
        job.status = "failed"
        job.error = str(exc)

    return {
        "message": "Enrichment queued",
        "job_id": str(job.id),
        "contact_id": str(contact_id),
    }


@router.post("/bulk-enrich", status_code=status.HTTP_202_ACCEPTED)
async def bulk_enrich(
    req: BulkEnrichRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue Instagram enrichment for multiple contacts."""
    # Verify all contacts belong to user
    result = await db.execute(
        select(Contact).where(
            Contact.id.in_(req.contact_ids),
            Contact.user_id == current_user.id,
        )
    )
    found_contacts = result.scalars().all()
    found_ids = {c.id for c in found_contacts}

    jobs = []
    for cid in req.contact_ids:
        if cid not in found_ids:
            continue
        job = EnrichmentJob(
            user_id=current_user.id,
            entity_type="contact",
            entity_id=cid,
            job_type="ig_enrichment",
            status="queued",
        )
        db.add(job)
        jobs.append(job)

    await db.flush()

    try:
        from app.tasks.enrichment import enrich_contact_instagram
        for job, cid in zip(jobs, [c.id for c in found_contacts]):
            task = enrich_contact_instagram.delay(str(cid), str(current_user.id))
            job.celery_task_id = task.id
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning(f"Celery unavailable: {exc}")

    return {
        "message": "Bulk enrichment queued",
        "queued": len(jobs),
        "job_ids": [str(j.id) for j in jobs],
    }


@router.post("/enrich-all-pending", status_code=status.HTTP_202_ACCEPTED)
async def enrich_all_pending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue enrichment for all contacts with enrichment_status='pending'."""
    result = await db.execute(
        select(Contact).where(
            Contact.user_id == current_user.id,
            Contact.enrichment_status == "pending",
            Contact.instagram_handle.is_(None),
        ).limit(200)  # Safety cap
    )
    contacts = result.scalars().all()

    if not contacts:
        return {"message": "No pending contacts", "queued": 0}

    jobs = []
    for contact in contacts:
        job = EnrichmentJob(
            user_id=current_user.id,
            entity_type="contact",
            entity_id=contact.id,
            job_type="ig_enrichment",
            status="queued",
        )
        db.add(job)
        jobs.append((job, contact.id))

    await db.flush()

    try:
        from app.tasks.enrichment import enrich_contact_instagram
        for job, cid in jobs:
            task = enrich_contact_instagram.delay(str(cid), str(current_user.id))
            job.celery_task_id = task.id
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).warning(f"Celery unavailable: {exc}")

    return {
        "message": f"Queued {len(jobs)} contacts for enrichment",
        "queued": len(jobs),
    }
