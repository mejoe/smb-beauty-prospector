"""
Company Discovery Tasks - Sprint 3

STUBBED APIs with realistic mock data.
To enable live discovery, set these env vars:
  GOOGLE_PLACES_API_KEY - Google Places API (New) key
  YELP_API_KEY          - Yelp Fusion API key

Both stubs return data in the same format as the real APIs would,
so replacing the stub with a real HTTP call is straightforward.
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# ─── API keys (set these in .env to use real APIs) ────────────────────────────
# TODO: Set GOOGLE_PLACES_API_KEY in .env to enable real Google Places search
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
# TODO: Set YELP_API_KEY in .env to enable real Yelp Fusion search
YELP_API_KEY = os.getenv("YELP_API_KEY")


# ─── Stub data ────────────────────────────────────────────────────────────────

_STUB_GOOGLE_PLACES = [
    {
        "name": "Luxe Aesthetics & MedSpa",
        "formatted_address": "1234 Main St, Austin, TX 78701",
        "city": "Austin", "state": "TX",
        "formatted_phone_number": "(512) 555-0101",
        "website": "https://luxeaesthetics.com",
        "place_id": "ChIJstub0001",
        "instagram_handle": "luxeaesthetics_atx",
        "source": "google_places",
    },
    {
        "name": "Radiance MedSpa",
        "formatted_address": "5678 Congress Ave, Austin, TX 78704",
        "city": "Austin", "state": "TX",
        "formatted_phone_number": "(512) 555-0102",
        "website": "https://radiancemedspa.com",
        "place_id": "ChIJstub0002",
        "source": "google_places",
    },
    {
        "name": "Pure Skin Studio",
        "formatted_address": "910 S Lamar Blvd, Austin, TX 78704",
        "city": "Austin", "state": "TX",
        "formatted_phone_number": "(512) 555-0103",
        "website": "https://pureskinstudio.com",
        "place_id": "ChIJstub0003",
        "instagram_handle": "pureskinstudio",
        "source": "google_places",
    },
    {
        "name": "Glow & Go Aesthetics",
        "formatted_address": "222 W 2nd St, Austin, TX 78701",
        "city": "Austin", "state": "TX",
        "formatted_phone_number": "(512) 555-0104",
        "website": "https://glowandgo.com",
        "place_id": "ChIJstub0004",
        "source": "google_places",
    },
    {
        "name": "Revive Wellness Clinic",
        "formatted_address": "3330 Bee Caves Rd, Austin, TX 78746",
        "city": "Austin", "state": "TX",
        "formatted_phone_number": "(512) 555-0105",
        "website": "https://revivewellness.com",
        "place_id": "ChIJstub0005",
        "instagram_handle": "revive_wellness_atx",
        "source": "google_places",
    },
]

_STUB_YELP = [
    {
        "name": "Glow & Go Aesthetics",  # intentional dupe with Google Places to test dedup
        "location": {"address1": "222 W 2nd St", "city": "Austin", "state": "TX", "zip_code": "78701"},
        "phone": "+15125550104",
        "url": "https://yelp.com/biz/glow-and-go",
        "rating": 4.8,
        "review_count": 127,
        "source": "yelp",
    },
    {
        "name": "Skin Lab Medical Aesthetics",
        "location": {"address1": "4400 N Lamar Blvd", "city": "Austin", "state": "TX", "zip_code": "78756"},
        "phone": "+15125550201",
        "url": "https://yelp.com/biz/skin-lab",
        "rating": 4.9,
        "review_count": 84,
        "source": "yelp",
    },
    {
        "name": "The Aesthetic Suite",
        "location": {"address1": "2110 Ranch Rd 620 N", "city": "Austin", "state": "TX", "zip_code": "78734"},
        "phone": "+15125550202",
        "url": "https://yelp.com/biz/aesthetic-suite",
        "rating": 4.7,
        "review_count": 61,
        "source": "yelp",
    },
    {
        "name": "Float ATX Wellness",
        "location": {"address1": "1001 E 5th St", "city": "Austin", "state": "TX", "zip_code": "78702"},
        "phone": "+15125550203",
        "url": "https://yelp.com/biz/float-atx",
        "rating": 4.6,
        "review_count": 203,
        "source": "yelp",
    },
]


# ─── Real API stubs ───────────────────────────────────────────────────────────

def _search_google_places(query: str, location: str, api_key: str) -> list[dict]:
    """
    TODO: Replace with real Google Places API call.
    Endpoint: https://maps.googleapis.com/maps/api/place/textsearch/json
    Params: query=medspa+{location}, key={api_key}
    """
    import requests  # type: ignore
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"{query} {location}", "key": api_key, "type": "health"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    companies = []
    for r in results:
        companies.append({
            "name": r.get("name"),
            "formatted_address": r.get("formatted_address"),
            "city": r.get("formatted_address", "").split(",")[1].strip() if "," in r.get("formatted_address", "") else "",
            "state": r.get("formatted_address", "").split(",")[2].strip()[:2] if len(r.get("formatted_address", "").split(",")) > 2 else "",
            "place_id": r.get("place_id"),
            "source": "google_places",
        })
    return companies


def _search_yelp(term: str, location: str, api_key: str) -> list[dict]:
    """
    TODO: Replace with real Yelp Fusion API call.
    Endpoint: https://api.yelp.com/v3/businesses/search
    Headers: Authorization: Bearer {api_key}
    """
    import requests  # type: ignore
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"term": term, "location": location, "categories": "medspa,skincare", "limit": 50}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("businesses", [])


# ─── Normalizer ───────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    name = name.lower()
    stopwords = ["spa", "medical", "med", "clinic", "center", "aesthetics",
                 "beauty", "wellness", "the", "of", "and", "&"]
    for word in stopwords:
        name = re.sub(rf'\b{word}\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _normalize_google(r: dict) -> dict:
    return {
        "name": r["name"],
        "name_normalized": _normalize_name(r["name"]),
        "address": r.get("formatted_address"),
        "city": r.get("city"),
        "state": r.get("state"),
        "phone": r.get("formatted_phone_number"),
        "website": r.get("website"),
        "google_place_id": r.get("place_id"),
        "instagram_handle": r.get("instagram_handle"),
        "source": "google_places",
    }


def _normalize_yelp(r: dict) -> dict:
    loc = r.get("location", {})
    city = loc.get("city")
    state = loc.get("state")
    address_parts = [loc.get("address1"), loc.get("city"), loc.get("state"), loc.get("zip_code")]
    address = ", ".join(p for p in address_parts if p)
    return {
        "name": r["name"],
        "name_normalized": _normalize_name(r["name"]),
        "address": address,
        "city": city,
        "state": state,
        "phone": r.get("phone"),
        "yelp_url": r.get("url"),
        "yelp_rating": r.get("rating"),
        "yelp_review_count": r.get("review_count"),
        "source": "yelp",
    }


def _merge_and_dedup(google_results: list, yelp_results: list) -> list[dict]:
    """Merge results; deduplicate by name_normalized + city."""
    seen: dict[str, dict] = {}
    for r in google_results + yelp_results:
        key = f"{r['name_normalized']}_{(r.get('city') or '').lower()}"
        if key not in seen:
            seen[key] = r
        else:
            # Merge: fill missing fields from the second source
            existing = seen[key]
            for k, v in r.items():
                if v and not existing.get(k):
                    existing[k] = v
    return list(seen.values())


# ─── Celery Task ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.tasks.discovery.discover_companies")
def discover_companies(self, job_id: str, session_id: str, search_config: dict, user_id: str):
    """
    Discover companies from Google Places + Yelp, merge, deduplicate, and store.

    search_config keys:
      - location: str (e.g. "Austin, TX")
      - industry: str (e.g. "medspa")
      - radius_miles: int

    TODO: Set GOOGLE_PLACES_API_KEY and YELP_API_KEY env vars for live discovery.
    """
    import uuid as uuid_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession
    from app.config import settings
    from app.models.company import Company
    from app.models.enrichment import EnrichmentJob

    logger.info(f"discover_companies: job={job_id} session={session_id} config={search_config}")

    # Use sync engine for Celery task
    sync_url = settings.DATABASE_URL_SYNC
    engine = create_engine(sync_url, pool_pre_ping=True)

    location = search_config.get("location", "Austin, TX")
    industry = search_config.get("industry", "medspa")

    # ── Fetch from APIs (real or stub) ───────────────────────────────────────
    google_raw = []
    yelp_raw = []

    if GOOGLE_PLACES_API_KEY:
        try:
            google_raw = _search_google_places(industry, location, GOOGLE_PLACES_API_KEY)
            logger.info(f"Google Places returned {len(google_raw)} results")
        except Exception as exc:
            logger.error(f"Google Places API error: {exc}")
    else:
        # STUB: Return realistic mock data
        logger.info("GOOGLE_PLACES_API_KEY not set — using stub data")
        google_raw = _STUB_GOOGLE_PLACES

    if YELP_API_KEY:
        try:
            yelp_raw = _search_yelp(industry, location, YELP_API_KEY)
            logger.info(f"Yelp returned {len(yelp_raw)} results")
        except Exception as exc:
            logger.error(f"Yelp API error: {exc}")
    else:
        # STUB: Return realistic mock data
        logger.info("YELP_API_KEY not set — using stub data")
        yelp_raw = _STUB_YELP

    google_norm = [_normalize_google(r) for r in google_raw]
    yelp_norm = [_normalize_yelp(r) for r in yelp_raw]
    merged = _merge_and_dedup(google_norm, yelp_norm)

    logger.info(f"Merged {len(merged)} unique companies (from {len(google_norm)} Google + {len(yelp_norm)} Yelp)")

    # ── Store to DB ──────────────────────────────────────────────────────────
    user_uuid = uuid_mod.UUID(user_id)
    session_uuid = uuid_mod.UUID(session_id)
    job_uuid = uuid_mod.UUID(job_id)
    stored = 0

    with SyncSession(engine) as db:
        # Load existing normalized names to dedup against stored companies
        existing_norms = {
            row[0] for row in db.execute(
                Company.__table__.select()
                .with_only_columns(Company.name_normalized)
                .where(Company.user_id == user_uuid)
            )
        }

        for c in merged:
            if c.get("name_normalized") in existing_norms:
                continue  # skip already-stored

            company = Company(
                user_id=user_uuid,
                session_id=session_uuid,
                name=c["name"],
                name_normalized=c["name_normalized"],
                city=c.get("city"),
                state=c.get("state"),
                address=c.get("address"),
                phone=c.get("phone"),
                website=c.get("website"),
                instagram_handle=c.get("instagram_handle"),
                yelp_url=c.get("yelp_url"),
                yelp_rating=c.get("yelp_rating"),
                yelp_review_count=c.get("yelp_review_count"),
                google_place_id=c.get("google_place_id"),
                source=c.get("source", "discovery"),
                category=search_config.get("industry", "medspa"),
            )
            db.add(company)
            existing_norms.add(c["name_normalized"])
            stored += 1

        # Update job status
        job = db.get(EnrichmentJob, job_uuid)
        if job:
            job.status = "complete"
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"companies_found": len(merged), "companies_stored": stored}

        db.commit()

    logger.info(f"Discovery complete: {stored} new companies stored")
    return {"status": "complete", "companies_found": len(merged), "companies_stored": stored}


# ─── Legacy stub task (keep for backward compat) ─────────────────────────────

@celery_app.task(bind=True, name="app.tasks.discovery.run_company_discovery")
def run_company_discovery(self, session_id: str, search_config: dict, user_id: str):
    """Legacy stub task - Sprint 1. Use discover_companies for Sprint 3+."""
    logger.info(f"Discovery task legacy stub: session={session_id}")
    return {"status": "stub", "companies_found": 0}
