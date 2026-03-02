"""
AI Chat router - Sprint 2 implementation placeholder.
Full streaming SSE implementation in Sprint 2.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.session import ResearchSession
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str


@router.post("")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI Chat endpoint. Sprint 1: stub response.
    Sprint 2: full Claude streaming SSE implementation.
    """
    # Verify session belongs to user
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == req.session_id,
            ResearchSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    user_msg = ChatMessage(
        session_id=req.session_id,
        user_id=current_user.id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    await db.flush()

    # TODO: Sprint 2 - implement Claude streaming SSE
    stub_reply = (
        "Hi! I'm your B2B prospecting assistant for the beauty and aesthetic medicine industry. "
        "I can help you find MedSpas, plastic surgery centers, dermatology clinics, and more. "
        "Tell me: what cities or regions are you targeting, and what types of providers are you looking for?"
    )
    assistant_msg = ChatMessage(
        session_id=req.session_id,
        user_id=current_user.id,
        role="assistant",
        content=stub_reply,
    )
    db.add(assistant_msg)

    return {"reply": stub_reply, "message_id": str(assistant_msg.id)}


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in messages
    ]
