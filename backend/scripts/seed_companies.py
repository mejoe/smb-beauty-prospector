#!/usr/bin/env python3
"""
Seed script: Import 100 companies from the medspa market research CSV.

Usage (from backend/ directory):
    python scripts/seed_companies.py [--user-email admin@example.com] [--csv /path/to/companies.csv]

Defaults:
    CSV: /home/joemcbride/.openclaw/workspace/company-docs/medspa-market-research/companies.csv
    User: first user in DB, or creates a seed user if none exists
"""
import argparse
import csv
import os
import re
import sys
import asyncio

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_CSV = "/home/joemcbride/.openclaw/workspace/company-docs/medspa-market-research/companies.csv"
DEFAULT_EMAIL = "seed@beautyprospector.local"

import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.database import Base
from app.models.company import Company
from app.models.user import User


def normalize_name(name: str) -> str:
    name = name.lower()
    stopwords = ["spa", "medical", "med", "clinic", "center", "aesthetics",
                 "beauty", "wellness", "the", "of", "and", "&"]
    for word in stopwords:
        name = re.sub(rf'\b{word}\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


async def get_or_create_user(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    # Create seed user (password: seedpassword123)
    from app.services.auth import get_password_hash
    user = User(
        email=email,
        name="Seed User",
        hashed_password=get_password_hash("seedpassword123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    print(f"Created seed user: {email}")
    return user


async def seed(csv_path: str, user_email: str):
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} rows in CSV")

    async with SessionLocal() as db:
        user = await get_or_create_user(db, user_email)
        print(f"Seeding for user: {user.email} ({user.id})")

        # Load existing normalized names to dedup
        existing_result = await db.execute(
            select(Company.name_normalized).where(Company.user_id == user.id)
        )
        existing_norms = {row[0] for row in existing_result}

        imported = 0
        skipped = 0

        for row in rows:
            def col(*keys):
                for k in keys:
                    for rk in row.keys():
                        if rk.strip().lower() == k.lower():
                            v = row[rk]
                            return v.strip() if v else None
                return None

            name = col("Company", "name", "company_name")
            if not name:
                skipped += 1
                continue

            city = col("City", "city") or ""
            name_normalized = normalize_name(name)

            if name_normalized in existing_norms:
                skipped += 1
                continue

            instagram = col("Business Instagram", "instagram", "instagram_handle") or ""
            if instagram.startswith("@"):
                instagram = instagram[1:]

            company = Company(
                user_id=user.id,
                name=name,
                name_normalized=name_normalized,
                city=city,
                state=col("State", "state"),
                category=col("Category", "category", "industry"),
                address=col("Address", "address"),
                phone=col("Phone", "phone"),
                website=col("Website", "website"),
                instagram_handle=instagram or None,
                notes=col("Notes", "notes"),
                source="seed_import",
            )
            db.add(company)
            existing_norms.add(name_normalized)
            imported += 1

        await db.commit()
        print(f"\n✅ Done! Imported: {imported}, Skipped (dupes/empty): {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed companies from CSV")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to companies.csv")
    parser.add_argument("--user-email", default=DEFAULT_EMAIL, help="Email of user to assign companies to")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV not found: {args.csv}")
        sys.exit(1)

    asyncio.run(seed(args.csv, args.user_email))
