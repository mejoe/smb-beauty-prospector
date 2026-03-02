"""
AI Chat router - Sprint 2: Claude streaming SSE implementation.
"""
import json
import re
import uuid
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.session import ResearchSession
from app.models.enrichment import EnrichmentJob
from app.models.user import User
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """You are a B2B prospecting assistant for the beauty and aesthetic medicine industry.
Your job is to help sales professionals find high-quality prospect companies and contacts.

Guide the user through defining:
1. Industry segments: MedSpa, Plastic Surgery, Dermatology, Functional Medicine, Medical Weight Loss, Aesthetics
2. Target geographies: city, metro area, state, or nationwide
3. Target roles: owner, medical director, nurse practitioner, injector, aesthetician, office manager
4. Size qualifiers: minimum Instagram followers, minimum review count, number of locations
5. Service specialties: botox, fillers, laser, IV therapy, weight loss, etc.

When you have enough information, emit a search config block like:
<search_config>
{
  "industries": ["medspa"],
  "geographies": [{"city": "Austin", "state": "TX"}],
  "target_roles": ["owner", "medical_director"],
  "min_ig_followers": 1000,
  "min_yelp_reviews": 10,
  "services_include": ["botox", "fillers"],
  "max_results_per_geo": 50
}
</search_config>

You can also help users draft outreach messages, review discovered contacts,
suggest follow-up search strategies, and answer questions about the industry."""

STUB_RESPONSE_CHUNKS = [
    "Hi! I'm your B2B prospecting assistant for the beauty and aesthetic medicine industry. ",
    "I can help you find **MedSpas**, plastic surgery centers, dermatology clinics, and more.\n\n",
    "To get started, tell me:\n",
    "1. **What cities or regions** are you targeting?\n",
    "2. **What types of providers** are you looking for? (MedSpas, plastic surgery, dermatology, etc.)\n",
    "3. **What roles** are you trying to reach? (owners, medical directors, injectors, etc.)\n\n",
    "Once I have this info, I'll build a targeted search configuration for you.",
]


def extract_search_config(text: str) -> dict | None:
    """Extract and parse <search_config> JSON block from assistant response."""
    pattern = r"<search_config>\s*([\s\S]*?)\s*</search_config>"
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str


async def _stub_stream(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    user_message: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Return a canned streaming response when ANTHROPIC_API_KEY is not set."""
    # Persist user message
    user_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    full_response = ""
    for chunk in STUB_RESPONSE_CHUNKS:
        full_response += chunk
        event = json.dumps({"type": "token", "text": chunk})
        yield f"data: {event}\n\n"
        await asyncio.sleep(0.05)

    # Persist assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=full_response,
    )
    db.add(assistant_msg)
    await db.commit()

    done_event = json.dumps({"type": "done", "message_id": str(assistant_msg.id)})
    yield f"data: {done_event}\n\n"


async def _claude_stream(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    user_message: str,
    history: list[ChatMessage],
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream response from Claude, detect search_config, persist messages."""
    import anthropic

    # Persist user message first
    user_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    # Build messages for Claude (history + new user message)
    claude_messages = []
    for msg in history:
        claude_messages.append({"role": msg.role, "content": msg.content})
    claude_messages.append({"role": "user", "content": user_message})

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    full_response = ""
    try:
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=claude_messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                event = json.dumps({"type": "token", "text": text})
                yield f"data: {event}\n\n"

    except Exception as e:
        err_event = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {err_event}\n\n"
        await db.rollback()
        return

    # Detect search_config
    search_config = extract_search_config(full_response)
    metadata: dict = {}
    job_id: str | None = None

    if search_config:
        # Update session search_config
        result = await db.execute(
            select(ResearchSession).where(ResearchSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.search_config = search_config
            db.add(session)

        # Create a discovery job stub
        job = EnrichmentJob(
            user_id=user_id,
            entity_type="session",
            entity_id=session_id,
            job_type="company_discovery",
            status="queued",
        )
        db.add(job)
        await db.flush()
        job_id = str(job.id)
        metadata = {"triggered_search_config": search_config, "job_id": job_id}

    # Persist assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=full_response,
        msg_metadata=metadata if metadata else None,
    )
    db.add(assistant_msg)
    await db.commit()

    # Final metadata event
    done_payload: dict = {"type": "done", "message_id": str(assistant_msg.id)}
    if search_config:
        done_payload["search_config"] = search_config
        done_payload["job_id"] = job_id
    yield f"data: {json.dumps(done_payload)}\n\n"


@router.post("")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /chat — streams Claude response via SSE (text/event-stream).
    Each SSE event is a JSON object:
      {"type": "token", "text": "..."} — incremental text
      {"type": "done", "message_id": "...", "search_config": {...}, "job_id": "..."} — final
      {"type": "error", "message": "..."} — on failure
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

    # Load history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == req.session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history = history_result.scalars().all()

    use_stub = not settings.ANTHROPIC_API_KEY

    if use_stub:
        gen = _stub_stream(req.session_id, current_user.id, req.message, db)
    else:
        gen = _claude_stream(req.session_id, current_user.id, req.message, history, db)

    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "metadata": m.msg_metadata,
            "created_at": m.created_at,
        }
        for m in messages
    ]
