from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.enrichment import EnrichmentJob
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(EnrichmentJob).where(EnrichmentJob.user_id == current_user.id)
    if status:
        q = q.where(EnrichmentJob.status == status)
    q = q.order_by(EnrichmentJob.created_at.desc()).limit(limit)
    result = await db.execute(q)
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "entity_type": j.entity_type,
            "entity_id": str(j.entity_id),
            "job_type": j.job_type,
            "status": j.status,
            "error": j.error,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        }
        for j in jobs
    ]


@router.get("/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EnrichmentJob).where(
            EnrichmentJob.id == job_id,
            EnrichmentJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "entity_type": job.entity_type,
        "entity_id": str(job.entity_id),
        "job_type": job.job_type,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "celery_task_id": job.celery_task_id,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
