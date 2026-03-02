"""
Contact Enrichment Tasks - Sprints 5 & 6

Instagram enrichment (Sprint 5) - REAL implementation
LinkedIn enrichment (Sprint 6) - STUBBED
"""
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_full")
def enrich_contact_full(self, contact_id: str, user_id: str):
    """
    Full enrichment pipeline: Instagram (Method A/B/C) + LinkedIn.
    Sprint 1 stub. Sprint 5 will implement real IG enrichment.
    """
    logger.info(f"Enrichment stub: contact={contact_id}")
    # TODO: Sprint 5 - implement real Instagram enrichment
    return {"status": "stub", "contact_id": contact_id}


@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_instagram")
def enrich_contact_instagram(self, contact_id: str, user_id: str):
    """
    Instagram enrichment using Method A (followers) -> B (name search) -> C (hashtag).
    Sprint 5 full implementation.
    """
    # TODO: Sprint 5
    return {"status": "stub"}


@celery_app.task(bind=True, name="app.tasks.enrichment.enrich_contact_linkedin")
def enrich_contact_linkedin(self, contact_id: str, user_id: str):
    """
    LinkedIn enrichment via Apify actors.
    TODO: Set APIFY_API_KEY env var to enable.
    Sprint 6 full implementation.
    """
    # TODO: Sprint 6
    return {"status": "stub"}
