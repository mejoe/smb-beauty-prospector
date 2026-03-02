from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.dependencies import get_current_user
from app.services.encryption import encrypt, decrypt

router = APIRouter(prefix="/instagram", tags=["instagram"])


class IGSessionRequest(BaseModel):
    username: str
    cookies_json: str  # JSON string of session cookies captured from browser


class IGSessionStatus(BaseModel):
    connected: bool
    username: str | None
    valid_at: datetime | None
    expires_at: datetime | None


@router.get("/session-status", response_model=IGSessionStatus)
async def get_session_status(
    current_user: User = Depends(get_current_user),
):
    return IGSessionStatus(
        connected=current_user.ig_session_cookie is not None,
        username=current_user.ig_username,
        valid_at=current_user.ig_session_valid_at,
        expires_at=current_user.ig_session_expires_at,
    )


@router.post("/session", response_model=IGSessionStatus)
async def save_session(
    req: IGSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save Instagram session cookies (AES-256 encrypted)."""
    encrypted = encrypt(req.cookies_json)
    now = datetime.now(timezone.utc)
    current_user.ig_username = req.username
    current_user.ig_session_cookie = encrypted
    current_user.ig_session_valid_at = now
    # Sessions typically last ~90 days; we set a conservative 30-day expiry
    from datetime import timedelta
    current_user.ig_session_expires_at = now + timedelta(days=30)
    return IGSessionStatus(
        connected=True,
        username=current_user.ig_username,
        valid_at=current_user.ig_session_valid_at,
        expires_at=current_user.ig_session_expires_at,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Instagram account."""
    current_user.ig_username = None
    current_user.ig_session_cookie = None
    current_user.ig_session_valid_at = None
    current_user.ig_session_expires_at = None
