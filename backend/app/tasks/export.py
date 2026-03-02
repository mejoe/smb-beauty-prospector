"""
Export Tasks - Sprint 9
"""
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.export.generate_csv_export")
def generate_csv_export(self, user_id: str, filters: dict):
    """Sprint 9 - CSV export task."""
    # TODO: Sprint 9
    return {"status": "stub"}


@celery_app.task(bind=True, name="app.tasks.export.sync_to_google_sheets")
def sync_to_google_sheets(self, user_id: str, sheet_id: str, filters: dict):
    """
    Sprint 9 - Google Sheets sync.
    TODO: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.
    """
    # TODO: Sprint 9
    return {"status": "stub"}
