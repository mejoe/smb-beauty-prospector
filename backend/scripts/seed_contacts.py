#!/usr/bin/env python3
"""
Seed script: Import all 646 contacts from master_contacts_clean.csv
into the BeautyProspector database.

Usage:
    cd backend
    python scripts/seed_contacts.py

Environment:
    DATABASE_URL — defaults to sqlite+aiosqlite:///./beautyprospector.db
    SEED_EMAIL   — user account to seed under (default: admin@beautyprospector.com)
    SEED_PASSWORD — password for the account (default: changeme123)
    CSV_PATH     — path to contacts CSV (default: auto-detect)
"""
import csv
import os
import sys
import uuid
from pathlib import Path

# ─── Path setup ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

# Try multiple locations for the CSV
CSV_CANDIDATES = [
    Path(os.environ.get("CSV_PATH", "")),
    REPO_ROOT / "company-docs" / "medspa-market-research" / "master_contacts_clean.csv",
    Path.home() / ".openclaw" / "workspace" / "company-docs" / "medspa-market-research" / "master_contacts_clean.csv",
]

CSV_PATH = None
for p in CSV_CANDIDATES:
    if p and p.exists():
        CSV_PATH = p
        break

if CSV_PATH is None:
    print("ERROR: Could not find master_contacts_clean.csv")
    print("Set CSV_PATH env var or place it at:")
    for p in CSV_CANDIDATES[1:]:
        print(f"  {p}")
    sys.exit(1)

print(f"CSV: {CSV_PATH}")

# Add backend to path
sys.path.insert(0, str(BACKEND_DIR))

# ─── DB setup ─────────────────────────────────────────────────────────────────
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.database import Base
from app.models.user import User
from app.models.contact import Contact
from app.models.company import Company

SEED_EMAIL = os.environ.get("SEED_EMAIL", "admin@beautyprospector.com")
SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./beautyprospector.db")


def normalize_name(name: str) -> str:
    return name.lower().strip()


def clean_ig(handle: str | None) -> str | None:
    if not handle:
        return None
    handle = handle.strip().lstrip("@").strip()
    return handle or None


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # ── Find or create seed user ──────────────────────────────────────────
        result = await db.execute(select(User).where(User.email == SEED_EMAIL))
        user = result.scalar_one_or_none()

        if not user:
            from app.services.auth import AuthService
            try:
                user = await AuthService.register(db, SEED_EMAIL, SEED_PASSWORD, "Seed Admin")
                await db.flush()
                print(f"Created user: {SEED_EMAIL}")
            except Exception as e:
                print(f"Could not create user via AuthService: {e}")
                # Fallback: create manually
                from passlib.context import CryptContext
                pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
                user = User(
                    email=SEED_EMAIL,
                    hashed_password=pwd_ctx.hash(SEED_PASSWORD),
                    name="Seed Admin",
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                print(f"Created user (fallback): {SEED_EMAIL}")
        else:
            print(f"Using existing user: {SEED_EMAIL}")

        user_id = user.id

        # ── Build company name → id map ───────────────────────────────────────
        comp_result = await db.execute(
            select(Company.id, Company.name).where(Company.user_id == user_id)
        )
        company_map: dict[str, uuid.UUID] = {
            name.lower().strip(): cid for cid, name in comp_result.all()
        }

        # ── Read companies from CSV and create missing ones ───────────────────
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Collect unique company names from CSV
        csv_companies: dict[str, dict] = {}
        for row in rows:
            biz_name = (row.get("Business Name") or "").strip()
            city = (row.get("City") or "").strip()
            biz_type = (row.get("Business Type") or "").strip()
            if biz_name:
                key = biz_name.lower()
                if key not in csv_companies:
                    csv_companies[key] = {"name": biz_name, "city": city, "category": biz_type.lower() or "medspa"}

        # Create companies not already in DB
        new_companies = 0
        for key, info in csv_companies.items():
            if key not in company_map:
                company = Company(
                    user_id=user_id,
                    name=info["name"],
                    name_normalized=key,
                    city=info["city"],
                    category=info["category"],
                    source="csv_seed",
                )
                db.add(company)
                await db.flush()
                company_map[key] = company.id
                new_companies += 1

        print(f"Companies: {new_companies} created, {len(company_map) - new_companies} already existed")

        # ── Import contacts ───────────────────────────────────────────────────
        existing_result = await db.execute(
            select(Contact.name_normalized, Contact.company_id)
            .where(Contact.user_id == user_id)
        )
        existing_keys = {(r[0], str(r[1])) for r in existing_result.all()}

        imported = 0
        skipped = 0

        for row in rows:
            name = (row.get("Contact Name") or "").strip()
            if not name:
                skipped += 1
                continue

            name_norm = normalize_name(name)
            biz_name = (row.get("Business Name") or "").strip()
            company_id = company_map.get(biz_name.lower()) if biz_name else None

            dedup_key = (name_norm, str(company_id))
            if dedup_key in existing_keys:
                skipped += 1
                continue

            ig = clean_ig(row.get("Instagram"))
            linkedin = (row.get("LinkedIn") or "").strip() or None
            email = (row.get("Email") or "").strip() or None
            role = (row.get("Role") or "").strip() or None
            credentials = (row.get("Credentials") or "").strip() or None
            source = (row.get("Source") or "csv_seed").strip()

            contact = Contact(
                user_id=user_id,
                company_id=company_id,
                name=name,
                name_normalized=name_norm,
                role=role,
                credentials=credentials,
                email=email,
                linkedin_url=linkedin,
                instagram_handle=ig,
                source=source,
                enrichment_status="pending",
            )
            db.add(contact)
            existing_keys.add(dedup_key)
            imported += 1

            if imported % 100 == 0:
                print(f"  ... {imported} contacts imported so far")

        await db.commit()

    print(f"\n✅ Seed complete: {imported} contacts imported, {skipped} skipped")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
