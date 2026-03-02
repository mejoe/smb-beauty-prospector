"""
Contacts router - Sprint 4: Contact Discovery, Import/Export
"""
import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.contact import Contact
from app.models.company import Company
from app.models.enrichment import EnrichmentJob
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])

MAX_CSV_BYTES = 5 * 1024 * 1024  # 5MB


def normalize_name(name: str) -> str:
    return name.lower().strip()


def sanitize_csv_field(value: str) -> str:
    """Prevent CSV injection by stripping formula prefixes."""
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


# ─── List / Filter ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    company_id: uuid.UUID | None = Query(None),
    title: str | None = Query(None, description="Filter by title/role keyword"),
    has_email: bool | None = Query(None),
    has_linkedin: bool | None = Query(None),
    has_instagram: bool | None = Query(None),
    status: str | None = Query(None),
    enrichment_status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Contact.user_id == current_user.id]
    if company_id:
        conditions.append(Contact.company_id == company_id)
    if title:
        conditions.append(Contact.role.ilike(f"%{title}%"))
    if has_email is True:
        conditions.append(Contact.email.isnot(None))
    elif has_email is False:
        conditions.append(Contact.email.is_(None))
    if has_linkedin is True:
        conditions.append(Contact.linkedin_url.isnot(None))
    elif has_linkedin is False:
        conditions.append(Contact.linkedin_url.is_(None))
    if has_instagram is True:
        conditions.append(Contact.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Contact.instagram_handle.is_(None))
    if status:
        conditions.append(Contact.status == status)
    if enrichment_status:
        conditions.append(Contact.enrichment_status == enrichment_status)

    result = await db.execute(
        select(Contact)
        .where(and_(*conditions))
        .order_by(Contact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ─── Export CSV ───────────────────────────────────────────────────────────────

@router.get("/export")
async def export_contacts(
    company_id: uuid.UUID | None = Query(None),
    has_email: bool | None = Query(None),
    has_instagram: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export contacts to CSV."""
    conditions = [Contact.user_id == current_user.id]
    if company_id:
        conditions.append(Contact.company_id == company_id)
    if has_email is True:
        conditions.append(Contact.email.isnot(None))
    elif has_email is False:
        conditions.append(Contact.email.is_(None))
    if has_instagram is True:
        conditions.append(Contact.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Contact.instagram_handle.is_(None))

    result = await db.execute(
        select(Contact, Company.name.label("company_name"))
        .outerjoin(Company, Contact.company_id == Company.id)
        .where(and_(*conditions))
        .order_by(Contact.name)
    )
    rows = result.all()

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Name", "Role", "Credentials", "Company",
            "Email", "Phone", "LinkedIn", "Instagram",
            "Enrichment Status", "Status", "Source", "Notes",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for contact, company_name in rows:
            writer.writerow([
                sanitize_csv_field(contact.name or ""),
                sanitize_csv_field(contact.role or ""),
                contact.credentials or "",
                sanitize_csv_field(company_name or ""),
                contact.email or "",
                contact.phone or "",
                contact.linkedin_url or "",
                f"@{contact.instagram_handle}" if contact.instagram_handle else "",
                contact.enrichment_status,
                contact.status,
                contact.source or "",
                sanitize_csv_field(contact.crm_notes or ""),
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )


# ─── Import CSV ────────────────────────────────────────────────────────────────

@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_contacts(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import contacts from CSV.
    Expected columns (flexible, case-insensitive):
      Contact Name, Role, Credentials, Business Name / Company,
      Email, LinkedIn, Instagram, Source, Notes
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    # Normalize headers
    def h(row: dict, *keys: str) -> str | None:
        for k in keys:
            for rk in row:
                if rk.strip().lower() == k.lower():
                    v = row[rk]
                    return v.strip() if v else None
        return None

    # Build company name → id cache
    result = await db.execute(
        select(Company.id, Company.name).where(Company.user_id == current_user.id)
    )
    company_map: dict[str, uuid.UUID] = {
        name.lower().strip(): cid for cid, name in result.all()
    }

    # Existing contacts: name + company_id to dedup
    existing_result = await db.execute(
        select(Contact.name_normalized, Contact.company_id)
        .where(Contact.user_id == current_user.id)
    )
    existing_keys = {(row[0], str(row[1])) for row in existing_result.all()}

    imported = 0
    skipped = 0
    errors = []

    for row in reader:
        name = h(row, "Contact Name", "Name", "contact_name")
        if not name:
            skipped += 1
            continue

        name_norm = normalize_name(name)
        company_name_raw = h(row, "Business Name", "Company", "business_name")
        company_id: uuid.UUID | None = None
        if company_name_raw:
            company_id = company_map.get(company_name_raw.lower().strip())

        dedup_key = (name_norm, str(company_id))
        if dedup_key in existing_keys:
            skipped += 1
            continue

        # Clean instagram handle
        ig = h(row, "Instagram", "instagram_handle", "instagram")
        if ig:
            ig = ig.lstrip("@").strip() or None

        contact = Contact(
            user_id=current_user.id,
            company_id=company_id,
            name=name,
            name_normalized=name_norm,
            role=h(row, "Role", "Title", "role"),
            credentials=h(row, "Credentials", "credentials"),
            email=h(row, "Email", "email"),
            phone=h(row, "Phone", "phone"),
            linkedin_url=h(row, "LinkedIn", "linkedin_url", "linkedin"),
            instagram_handle=ig,
            source=h(row, "Source", "source") or "csv_import",
            crm_notes=h(row, "Notes", "crm_notes", "notes"),
        )
        db.add(contact)
        existing_keys.add(dedup_key)
        imported += 1

    await db.flush()
    return {"imported": imported, "skipped": skipped, "errors": errors}


# ─── Discover contacts for a company ──────────────────────────────────────────

@router.post("/discover/{company_id}", status_code=status.HTTP_202_ACCEPTED)
async def discover_contacts(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger contact discovery for a company.
    Creates an EnrichmentJob and fires the discover_contacts Celery task.
    """
    # Verify company belongs to user
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Create enrichment job
    job = EnrichmentJob(
        user_id=current_user.id,
        entity_type="company",
        entity_id=company_id,
        job_type="contact_discovery",
        status="queued",
    )
    db.add(job)
    await db.flush()

    # Fire Celery task
    try:
        from app.tasks.contact_discovery import discover_contacts as discover_task
        task = discover_task.delay(
            str(job.id),
            str(company_id),
            str(current_user.id),
        )
        job.celery_task_id = task.id
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Celery unavailable: {exc}")
        job.status = "failed"
        job.error = str(exc)

    return {
        "message": "Contact discovery queued",
        "job_id": str(job.id),
        "company_id": str(company_id),
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    req: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contact = Contact(
        user_id=current_user.id,
        company_id=req.company_id,
        name=req.name,
        name_normalized=normalize_name(req.name),
        role=req.role,
        credentials=req.credentials,
        email=req.email,
        phone=req.phone,
        linkedin_url=req.linkedin_url,
        instagram_handle=req.instagram_handle,
        source=req.source,
        crm_notes=req.crm_notes,
    )
    db.add(contact)
    await db.flush()
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    req: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in req.model_dump(exclude_none=True).items():
        if field == "name":
            contact.name_normalized = normalize_name(value)
        setattr(contact, field, value)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)


@router.post("/{contact_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger Instagram + LinkedIn enrichment for a contact."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # TODO: Sprint 5 — enqueue real enrichment task
    # from app.tasks.enrichment import enrich_contact_full
    # task = enrich_contact_full.delay(str(contact_id), str(current_user.id))
    return {"message": "Enrichment queued", "contact_id": str(contact_id), "job_id": "stub-job-id"}


@router.post("/bulk-enrich", status_code=status.HTTP_202_ACCEPTED)
async def bulk_enrich_contacts(
    contact_ids: list[uuid.UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger enrichment for multiple contacts."""
    return {"message": "Bulk enrichment queued", "count": len(contact_ids), "job_ids": []}
