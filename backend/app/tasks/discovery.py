"""
Company Discovery Tasks - Sprint 3

Stubbed with realistic mock data. Real API integrations ready via env vars.
TODO: Add real API keys to enable live discovery.
"""
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.discovery.run_company_discovery")
def run_company_discovery(self, session_id: str, search_config: dict, user_id: str):
    """
    Discovers companies from multiple sources based on search config.
    Sprint 1 stub - returns immediately.
    Sprint 3 will implement full Google Places + Yelp + SerpAPI + IG hashtag search.
    """
    logger.info(f"Discovery task stub: session={session_id}, config={search_config}")
    # TODO: Sprint 3 - implement real discovery
    return {"status": "stub", "companies_found": 0}
