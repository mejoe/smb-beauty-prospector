"""
Export router - Sprint 9 implementation placeholder.
"""
from fastapi import APIRouter, Depends
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/csv")
async def export_csv(current_user: User = Depends(get_current_user)):
    """Export contacts/companies to CSV. Full implementation in Sprint 9."""
    # TODO: Sprint 9 - implement CSV export
    return {"message": "CSV export not yet implemented", "sprint": 9}


@router.post("/sheets")
async def export_sheets(current_user: User = Depends(get_current_user)):
    """Sync to Google Sheets. Full implementation in Sprint 9."""
    # TODO: Sprint 9 - implement Google Sheets sync
    return {"message": "Google Sheets sync not yet implemented", "sprint": 9}
