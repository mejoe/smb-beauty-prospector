from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.database import get_db
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])


def normalize_name(name: str) -> str:
    return name.lower().strip()


@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    company_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    enrichment_status: str | None = Query(None),
    has_instagram: bool | None = Query(None),
    role: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Contact.user_id == current_user.id]
    if company_id:
        conditions.append(Contact.company_id == company_id)
    if status:
        conditions.append(Contact.status == status)
    if enrichment_status:
        conditions.append(Contact.enrichment_status == enrichment_status)
    if has_instagram is True:
        conditions.append(Contact.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Contact.instagram_handle.is_(None))
    if role:
        conditions.append(Contact.role.ilike(f"%{role}%"))

    result = await db.execute(
        select(Contact)
        .where(and_(*conditions))
        .order_by(Contact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


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

    # TODO: Enqueue enrichment task
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
    # TODO: Enqueue bulk enrichment tasks
    return {"message": "Bulk enrichment queued", "count": len(contact_ids), "job_ids": []}
