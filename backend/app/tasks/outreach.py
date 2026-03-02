"""
Outreach Tasks - Sprint 8

⚠️ DM SEND ENGINE - DO NOT ACTIVATE IN DEVELOPMENT
All actual sends are gated by a dev_mode check.
"""
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)

DEV_MODE = True  # Set to False only in production with explicit confirmation


@celery_app.task(bind=True, name="app.tasks.outreach.send_instagram_dm_campaign")
def send_instagram_dm_campaign(self, campaign_id: str, user_id: str):
    """
    ⚠️ DM BROADCAST ENGINE - DEVELOPMENT STUB
    Real implementation in Sprint 8.
    Sends will NEVER execute while DEV_MODE = True.
    """
    if DEV_MODE:
        logger.warning(f"[DEV MODE] DM campaign {campaign_id} would be sent here. Sends blocked.")
        return {"status": "dev_mode_blocked", "campaign_id": campaign_id}
    # TODO: Sprint 8 - implement real DM send engine with throttling
    raise NotImplementedError("DM send engine not yet implemented")
