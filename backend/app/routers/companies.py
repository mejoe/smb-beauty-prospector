"""
Companies router - Sprint 3: Discovery, import/export, full CRUD.
"""
import csv
import io
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.company import Company
from app.models.enrichment import EnrichmentJob
from app.models.user import User
from app.models.session import ResearchSession
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    CompanyDetailResponse, CompanySearchRequest,
)
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])

# CSV injection safe chars - strip leading = + - @ from field values
_CSV_UNSAFE = re.compile(r'^[=+\-@]')


def sanitize_csv_field(value: str) -> str:
    """Prevent CSV injection by prefixing dangerous chars."""
    if value and _CSV_UNSAFE.match(value):
        return "'" + value
    return value


def normalize_company_name(name: str) -> str:
    """Normalize company name for deduplication."""
    name = name.lower()
    stopwords = ["spa", "medical", "med", "clinic", "center", "aesthetics",
                 "beauty", "wellness", "the", "of", "and", "&"]
    for word in stopwords:
        name = re.sub(rf'\b{word}\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# ─── LIST ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),  # alias for category
    status: Optional[str] = Query(None),
    session_id: Optional[uuid.UUID] = Query(None),
    has_instagram: Optional[bool] = Query(None),
    has_linkedin: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Company.user_id == current_user.id]
    if city:
        conditions.append(Company.city.ilike(f"%{city}%"))
    if state:
        conditions.append(Company.state.ilike(f"%{state}%"))
    if category:
        conditions.append(Company.category == category)
    elif industry:
        conditions.append(Company.category == industry)
    if status:
        conditions.append(Company.status == status)
    if session_id:
        conditions.append(Company.session_id == session_id)
    if has_instagram is True:
        conditions.append(Company.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Company.instagram_handle.is_(None))
    if has_linkedin is True:
        conditions.append(Company.linkedin_url.isnot(None))
    elif has_linkedin is False:
        conditions.append(Company.linkedin_url.is_(None))

    result = await db.execute(
        select(Company)
        .where(and_(*conditions))
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ─── CREATE ──────────────────────────────────────────────────────────────────

@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    req: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = Company(
        user_id=current_user.id,
        session_id=req.session_id,
        name=req.name,
        name_normalized=normalize_company_name(req.name),
        city=req.city,
        state=req.state,
        category=req.category,
        address=req.address,
        phone=req.phone,
        website=req.website,
        instagram_handle=req.instagram_handle,
        linkedin_url=req.linkedin_url,
        notes=req.notes,
    )
    db.add(company)
    await db.flush()
    return company


# ─── SEARCH (DISCOVERY) ───────────────────────────────────────────────────────

@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def trigger_company_search(
    req: CompanySearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a company discovery job from a session's search_config.
    Creates an EnrichmentJob record, fires Celery task.
    """
    # Verify session belongs to user
    session_result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == req.session_id,
            ResearchSession.user_id == current_user.id
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Merge search_config from request + session
    search_config = {**(session.search_config or {}), **(req.search_config or {})}

    # Create discovery job
    job = EnrichmentJob(
        user_id=current_user.id,
        entity_type="session",
        entity_id=req.session_id,
        job_type="discover_companies",
        status="running",
    )
    db.add(job)
    await db.flush()

    # Fire Celery task (best-effort; task module imported lazily)
    celery_task_id = None
    try:
        from app.tasks.discovery import discover_companies
        task = discover_companies.delay(
            str(job.id),
            str(req.session_id),
            search_config,
            str(current_user.id),
        )
        celery_task_id = task.id
        job.celery_task_id = celery_task_id
    except Exception as exc:
        logger.warning(f"Celery unavailable, job {job.id} will run inline: {exc}")
        # If Celery isn't running (dev mode), mark job failed gracefully
        job.status = "failed"
        job.error = "Celery broker unavailable"

    return {
        "message": "Discovery job queued",
        "job_id": str(job.id),
        "session_id": str(req.session_id),
        "celery_task_id": celery_task_id,
    }


# ─── IMPORT ───────────────────────────────────────────────────────────────────

@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_companies_csv(
    file: UploadFile = File(...),
    session_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import companies from CSV.
    Expected columns: Company/name, City, Category, Address, Phone, Website,
                      Business Instagram (optional), Notes (optional)
    Deduplicates by name_normalized + city.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = await file.read()
    # Limit to 5MB
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV too large (max 5MB)")

    try:
        text = raw.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    # Flexible column mapping
    def col(row: dict, *keys: str) -> Optional[str]:
        for k in keys:
            for rk in row.keys():
                if rk.strip().lower() == k.lower():
                    v = row[rk]
                    return v.strip() if v else None
        return None

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, 1):
        try:
            name = col(row, "Company", "name", "company_name")
            if not name:
                skipped += 1
                continue

            city = col(row, "City", "city")
            name_normalized = normalize_company_name(name)

            # Dedup check
            existing = await db.execute(
                select(Company).where(
                    Company.user_id == current_user.id,
                    Company.name_normalized == name_normalized,
                    Company.city == city,
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            instagram = col(row, "Business Instagram", "instagram", "instagram_handle")
            if instagram and instagram.startswith("@"):
                instagram = instagram[1:]

            company = Company(
                user_id=current_user.id,
                session_id=session_id,
                name=name,
                name_normalized=name_normalized,
                city=city,
                state=col(row, "State", "state"),
                category=col(row, "Category", "category", "industry"),
                address=col(row, "Address", "address"),
                phone=col(row, "Phone", "phone"),
                website=col(row, "Website", "website"),
                instagram_handle=instagram,
                notes=col(row, "Notes", "notes"),
                source="csv_import",
            )
            db.add(company)
            imported += 1

        except Exception as exc:
            errors.append({"row": i, "error": str(exc)})

    await db.flush()
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10],  # cap error list
    }


# ─── EXPORT ───────────────────────────────────────────────────────────────────

@router.get("/export")
async def export_companies_csv(
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    has_instagram: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export companies to CSV. Filters match GET /companies."""
    conditions = [Company.user_id == current_user.id]
    if city:
        conditions.append(Company.city.ilike(f"%{city}%"))
    if state:
        conditions.append(Company.state.ilike(f"%{state}%"))
    if category:
        conditions.append(Company.category == category)
    if has_instagram is True:
        conditions.append(Company.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Company.instagram_handle.is_(None))

    result = await db.execute(
        select(Company).where(and_(*conditions)).order_by(Company.name)
    )
    companies = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "City", "State", "Category", "Address", "Phone",
        "Website", "Instagram", "LinkedIn", "Status",
        "Yelp Rating", "IG Followers", "Source", "Notes", "Created At",
    ])

    for c in companies:
        writer.writerow([
            sanitize_csv_field(c.name or ""),
            sanitize_csv_field(c.city or ""),
            sanitize_csv_field(c.state or ""),
            sanitize_csv_field(c.category or ""),
            sanitize_csv_field(c.address or ""),
            sanitize_csv_field(c.phone or ""),
            sanitize_csv_field(c.website or ""),
            sanitize_csv_field(f"@{c.instagram_handle}" if c.instagram_handle else ""),
            sanitize_csv_field(c.linkedin_url or ""),
            sanitize_csv_field(c.status or ""),
            str(c.yelp_rating) if c.yelp_rating else "",
            str(c.instagram_followers) if c.instagram_followers else "",
            sanitize_csv_field(c.source or ""),
            sanitize_csv_field(c.notes or ""),
            c.created_at.isoformat() if c.created_at else "",
        ])

    output.seek(0)
    filename = f"companies_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── DETAIL ──────────────────────────────────────────────────────────────────

@router.get("/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Contact count
    from app.models.contact import Contact
    count_result = await db.execute(
        select(func.count()).where(Contact.company_id == company_id)
    )
    contact_count = count_result.scalar() or 0

    resp = CompanyDetailResponse.model_validate(company)
    resp.contact_count = contact_count
    return resp


# ─── UPDATE ──────────────────────────────────────────────────────────────────

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    req: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in req.model_dump(exclude_none=True).items():
        if field == "name":
            company.name_normalized = normalize_company_name(value)
        setattr(company, field, value)
    return company


# ─── DELETE ──────────────────────────────────────────────────────────────────

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.delete(company)
