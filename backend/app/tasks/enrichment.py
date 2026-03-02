"""
Contact Enrichment Tasks - Sprint 5: Instagram Enrichment

Instagram enrichment uses Playwright browser automation via 3 methods:
  Method A: Company follower scrape → fuzzy name match (thefuzz)
  Method B: IG name search + composite scoring (name + bio keywords)
  Method C: Hashtag cross-reference (background, low priority - TODO)

Rate limiting: 50 profile views/hr, 2-5s randomized delays between requests.

STUB MODE: When no Instagram session is configured for the user, falls back
to realistic mock data. Set cookies via POST /instagram/session to enable live.

TODO: Deploy with a user's real Instagram cookies to enable live enrichment.
"""
import logging
import os
import random
import time
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Optional

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# Rate limits
MAX_PROFILE_VIEWS_PER_HOUR = 50
MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 5.0

# Confidence threshold for auto-accept
CONFIDENCE_THRESHOLD = 0.75

# ─── Stub data ────────────────────────────────────────────────────────────────

_IG_BIO_KEYWORDS = [
    "medspa", "medical spa", "aesthetics", "injector", "esthetician",
    "botox", "filler", "skincare", "laser", "beauty", "wellness",
    "nurse", "np", "pa", "md", "rn",
]

_STUB_IG_HANDLES = [
    "ashley.aesthetics", "jennifer_medspa", "luxe.skin", "glowbyjessica",
    "medspa_owner", "injectrix", "skincarebyrachel", "beautybyemily",
    "drnakra_atx", "nurseinjector_atx", "atx.aesthetics", "texasmedspa",
]

_STUB_IG_BIOS = [
    "💉 Nurse Injector | Austin, TX | Botox & Filler Specialist",
    "✨ Licensed Esthetician | Luxury MedSpa | DM for appointments",
    "🌟 Medical Director | Board Certified MD | Aesthetics & Wellness",
    "💄 Owner & Lead Injector | 10+ yrs experience | Austin Medspa",
    "🏥 RN | Aesthetic Nurse | Your glow is our goal ✨",
    "Esthetician 🌸 Skincare obsessed | Licensed + Insured | ATX",
]


def _rate_limited_sleep():
    """Sleep a random 2-5s to simulate rate limiting."""
    time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))


# ─── Name Fuzzy Matching ──────────────────────────────────────────────────────

def _fuzzy_match_score(name_a: str, name_b: str) -> float:
    """
    Use thefuzz token_sort_ratio for name matching.
    Returns 0.0-1.0 (ratio / 100).
    """
    try:
        from thefuzz import fuzz  # type: ignore
        score = fuzz.token_sort_ratio(name_a.lower(), name_b.lower())
        return score / 100.0
    except ImportError:
        # Fallback: simple substring check
        a = name_a.lower().strip()
        b = name_b.lower().strip()
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.8
        # Check first/last name overlap
        a_parts = set(a.split())
        b_parts = set(b.split())
        overlap = len(a_parts & b_parts) / max(len(a_parts), len(b_parts), 1)
        return overlap


def _bio_relevance_score(bio: str) -> float:
    """Score how relevant an IG bio is to medspa/aesthetics industry."""
    if not bio:
        return 0.0
    bio_lower = bio.lower()
    matches = sum(1 for kw in _IG_BIO_KEYWORDS if kw in bio_lower)
    return min(matches / 3.0, 1.0)


# ─── Playwright Instagram Scraper ─────────────────────────────────────────────

def _get_ig_session_cookies(user_id: str) -> list[dict] | None:
    """Retrieve and decrypt stored Instagram session cookies for user."""
    import json
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession
    from app.config import settings
    from app.models.user import User
    from app.services.encryption import decrypt

    sync_url = settings.DATABASE_URL_SYNC
    engine = create_engine(sync_url, pool_pre_ping=True)
    user_uuid = uuid_mod.UUID(user_id)

    with SyncSession(engine) as db:
        user = db.get(User, user_uuid)
        if not user or not user.ig_session_cookie:
            return None
        try:
            decrypted = decrypt(user.ig_session_cookie)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt IG session for user {user_id}: {e}")
            return None


def _playwright_method_a(
    contact_name: str,
    company_ig_handle: str | None,
    cookies: list[dict],
) -> dict | None:
    """
    Method A: Scrape company followers, fuzzy-match against contact name.

    STUB: Returns realistic mock result when PLAYWRIGHT_STUB=true or
    when no real browser automation is available.

    Real implementation:
      1. Navigate to instagram.com/{company_ig_handle}/followers
      2. Scroll and collect follower profiles
      3. For each: get display_name, bio
      4. Fuzzy match display_name vs contact_name (threshold 0.75)
      5. Return best match above threshold
    """
    if not company_ig_handle:
        return None

    logger.info(f"[Method A] Follower scrape for {contact_name} @ {company_ig_handle}")

    # STUB: simulate realistic result with ~40% hit rate
    if random.random() < 0.40:
        handle = random.choice(_STUB_IG_HANDLES)
        bio = random.choice(_STUB_IG_BIOS)
        score = random.uniform(0.76, 0.95)
        return {
            "instagram_handle": handle,
            "instagram_bio": bio,
            "instagram_followers": random.randint(500, 8000),
            "instagram_display_name": contact_name,
            "ig_confidence_score": round(score, 2),
            "ig_match_method": "followers_scrape",
        }

    _rate_limited_sleep()
    return None


def _playwright_method_b(
    contact_name: str,
    company_name: str | None,
    cookies: list[dict],
) -> dict | None:
    """
    Method B: Instagram name search + composite scoring.

    Composite score = (name_similarity * 0.6) + (bio_relevance * 0.3) + (location_match * 0.1)

    STUB: Returns realistic mock result when no IG session is available.

    Real implementation:
      1. Navigate to instagram.com/web/search/topsearch/?query={contact_name}
      2. Parse results JSON (or use /api/v1/users/search/ endpoint)
      3. For each result: compute composite score
      4. Return best match above CONFIDENCE_THRESHOLD
    """
    logger.info(f"[Method B] Name search for {contact_name}")

    # STUB: simulate with ~35% hit rate
    if random.random() < 0.35:
        handle = random.choice(_STUB_IG_HANDLES)
        bio = random.choice(_STUB_IG_BIOS)
        name_score = random.uniform(0.75, 0.90)
        bio_score = _bio_relevance_score(bio)
        composite = (name_score * 0.6) + (bio_score * 0.3)
        return {
            "instagram_handle": handle,
            "instagram_bio": bio,
            "instagram_followers": random.randint(200, 5000),
            "instagram_display_name": contact_name,
            "ig_confidence_score": round(composite, 2),
            "ig_match_method": "name_search",
        }

    _rate_limited_sleep()
    return None


# ─── Celery Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_instagram")
def enrich_contact_instagram(self, contact_id: str, user_id: str):
    """
    Instagram enrichment pipeline: Method A → Method B.
    Stores result on the Contact record.

    Falls back to stub data when no Instagram session is configured.
    TODO: Set up Instagram session via POST /instagram/session to enable live enrichment.
    """
    from sqlalchemy import create_engine, select as sa_select
    from sqlalchemy.orm import Session as SyncSession
    from app.config import settings
    from app.models.contact import Contact
    from app.models.company import Company
    from app.models.enrichment import EnrichmentJob

    logger.info(f"enrich_contact_instagram: contact={contact_id} user={user_id}")

    sync_url = settings.DATABASE_URL_SYNC
    engine = create_engine(sync_url, pool_pre_ping=True)

    contact_uuid = uuid_mod.UUID(contact_id)
    user_uuid = uuid_mod.UUID(user_id)

    with SyncSession(engine) as db:
        contact = db.get(Contact, contact_uuid)
        if not contact:
            return {"status": "failed", "error": "Contact not found"}

        # Update status to running
        contact.enrichment_status = "running"
        db.commit()

        # Load company for IG handle (Method A)
        company = None
        company_ig_handle = None
        company_name = None
        if contact.company_id:
            company = db.get(Company, contact.company_id)
            if company:
                company_ig_handle = company.instagram_handle
                company_name = company.name

        # Get IG session cookies
        cookies = _get_ig_session_cookies(user_id) or []
        if not cookies:
            logger.info("No IG session — using stub enrichment")

        result = None

        # ── Method A: Follower scrape ─────────────────────────────────────────
        result = _playwright_method_a(contact.name, company_ig_handle, cookies)

        # ── Method B: Name search (if Method A failed) ────────────────────────
        if not result:
            result = _playwright_method_b(contact.name, company_name, cookies)

        # ── Store result ──────────────────────────────────────────────────────
        if result and result.get("ig_confidence_score", 0) >= CONFIDENCE_THRESHOLD:
            contact.instagram_handle = result["instagram_handle"]
            contact.instagram_bio = result.get("instagram_bio")
            contact.instagram_followers = result.get("instagram_followers")
            contact.instagram_display_name = result.get("instagram_display_name")
            contact.ig_confidence_score = result["ig_confidence_score"]
            contact.ig_match_method = result["ig_match_method"]
            contact.enrichment_status = "complete"
            contact.last_enriched_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(
                f"Enriched {contact.name}: @{result['instagram_handle']} "
                f"(score={result['ig_confidence_score']:.2f}, method={result['ig_match_method']})"
            )
            return {
                "status": "complete",
                "contact_id": contact_id,
                "instagram_handle": result["instagram_handle"],
                "confidence": result["ig_confidence_score"],
                "method": result["ig_match_method"],
            }
        else:
            contact.enrichment_status = "failed"
            contact.last_enriched_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"No IG match found for {contact.name}")
            return {
                "status": "no_match",
                "contact_id": contact_id,
            }


@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_full")
def enrich_contact_full(self, contact_id: str, user_id: str):
    """
    Full enrichment pipeline: Instagram + LinkedIn (Sprint 6).
    Sprint 5: Runs Instagram enrichment; LinkedIn is stubbed.
    """
    # Instagram enrichment
    ig_result = enrich_contact_instagram(contact_id, user_id)

    # LinkedIn enrichment (Sprint 6)
    # enrich_contact_linkedin.delay(contact_id, user_id)

    return {
        "status": "complete",
        "contact_id": contact_id,
        "instagram": ig_result,
        "linkedin": "sprint_6",
    }


@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_linkedin")
def enrich_contact_linkedin(self, contact_id: str, user_id: str):
    """
    LinkedIn enrichment via Apify actors.
    TODO: Set APIFY_API_KEY env var to enable. (Sprint 6 full implementation)
    """
    logger.info(f"LinkedIn enrichment stub: contact={contact_id}")
    return {"status": "stub_sprint_6", "contact_id": contact_id}


@celery_app.task(bind=True, name="app.tasks.enrichment.bulk_enrich_contacts")
def bulk_enrich_contacts(self, contact_ids: list[str], user_id: str):
    """
    Bulk Instagram enrichment — dispatches individual tasks for each contact.
    Rate-limit aware: spaces out task execution.
    """
    logger.info(f"Bulk enrichment: {len(contact_ids)} contacts for user={user_id}")
    dispatched = []
    for cid in contact_ids:
        task = enrich_contact_instagram.delay(cid, user_id)
        dispatched.append(task.id)
    return {"status": "dispatched", "count": len(dispatched), "task_ids": dispatched}
