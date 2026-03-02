from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanySearchRequest
from app.dependencies import get_current_user

router = APIRouter(prefix="/companies", tags=["companies"])


def normalize_company_name(name: str) -> str:
    """Normalize company name for deduplication."""
    import re
    name = name.lower()
    # Remove common filler words
    stopwords = ["spa", "medical", "med", "clinic", "center", "aesthetics",
                 "beauty", "wellness", "the", "of", "and", "&"]
    for word in stopwords:
        name = re.sub(rf'\b{word}\b', '', name)
    # Remove punctuation and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    city: str | None = Query(None),
    category: str | None = Query(None),
    status: str | None = Query(None),
    session_id: uuid.UUID | None = Query(None),
    has_instagram: bool | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Company.user_id == current_user.id]
    if city:
        conditions.append(Company.city.ilike(f"%{city}%"))
    if category:
        conditions.append(Company.category == category)
    if status:
        conditions.append(Company.status == status)
    if session_id:
        conditions.append(Company.session_id == session_id)
    if has_instagram is True:
        conditions.append(Company.instagram_handle.isnot(None))
    elif has_instagram is False:
        conditions.append(Company.instagram_handle.is_(None))

    result = await db.execute(
        select(Company)
        .where(and_(*conditions))
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


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
        notes=req.notes,
    )
    db.add(company)
    await db.flush()
    return company


@router.get("/{company_id}", response_model=CompanyResponse)
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
    return company


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


@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def trigger_company_search(
    req: CompanySearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a company discovery job. Returns job_id for polling."""
    # TODO: Enqueue Celery discovery task
    # from app.tasks.discovery import run_company_discovery
    # task = run_company_discovery.delay(str(req.session_id), req.search_config, str(current_user.id))
    return {
        "message": "Discovery job queued",
        "job_id": "stub-job-id",  # TODO: return real Celery task ID
        "session_id": str(req.session_id),
    }
