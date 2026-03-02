"""
Tests for chat endpoint — Sprint 2.
Covers: SSE streaming stub, search_config detection, message persistence.
"""
import json
import re
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db
from app.routers.chat import extract_search_config

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register_and_login(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "chattest@example.com",
        "password": "testpass123",
        "name": "Chat Tester",
    })
    resp = await client.post("/auth/login", json={
        "email": "chattest@example.com",
        "password": "testpass123",
    })
    return resp.json()["access_token"]


# ─── Unit tests: extract_search_config ───────────────────────────────────────

class TestExtractSearchConfig:
    def test_valid_block(self):
        text = """Sure! Here is your config:
<search_config>
{
  "industries": ["medspa"],
  "geographies": [{"city": "Austin", "state": "TX"}],
  "target_roles": ["owner"]
}
</search_config>
Let me know if you want to adjust."""
        result = extract_search_config(text)
        assert result is not None
        assert result["industries"] == ["medspa"]
        assert result["geographies"][0]["city"] == "Austin"
        assert result["target_roles"] == ["owner"]

    def test_no_block(self):
        text = "Hello! I can help you find medspas in Austin."
        assert extract_search_config(text) is None

    def test_invalid_json_inside_block(self):
        text = "<search_config>NOT JSON</search_config>"
        assert extract_search_config(text) is None

    def test_full_config(self):
        text = """<search_config>
{
  "industries": ["medspa", "dermatology"],
  "geographies": [{"city": "Austin", "state": "TX"}, {"city": "Dallas", "state": "TX"}],
  "target_roles": ["owner", "medical_director"],
  "min_ig_followers": 1000,
  "min_yelp_reviews": 10,
  "services_include": ["botox", "fillers"],
  "max_results_per_geo": 50
}
</search_config>"""
        result = extract_search_config(text)
        assert result["min_ig_followers"] == 1000
        assert len(result["geographies"]) == 2
        assert "fillers" in result["services_include"]

    def test_whitespace_around_json(self):
        text = "<search_config>   \n  {\"industries\": [\"medspa\"]}  \n  </search_config>"
        result = extract_search_config(text)
        assert result == {"industries": ["medspa"]}


# ─── Integration tests: /chat endpoint ───────────────────────────────────────

class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient):
        resp = await client.post("/chat", json={
            "session_id": "00000000-0000-0000-0000-000000000001",
            "message": "hello",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_unknown_session(self, client: AsyncClient):
        token = await register_and_login(client)
        resp = await client.post(
            "/chat",
            json={
                "session_id": "00000000-0000-0000-0000-000000000001",
                "message": "hello",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # SSE is a streaming response; 404 is raised before streaming starts
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_stub_streaming(self, client: AsyncClient):
        """With no ANTHROPIC_API_KEY the stub stream should emit SSE events."""
        token = await register_and_login(client)

        # Create a session
        sess_resp = await client.post(
            "/sessions",
            json={"name": "Test Session"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sess_resp.status_code == 201
        session_id = sess_resp.json()["id"]

        # Chat — consume raw SSE
        resp = await client.post(
            "/chat",
            json={"session_id": session_id, "message": "What cities do you cover?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        # Parse SSE events
        events = []
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(token_events) > 0, "Should have token events"
        assert len(done_events) == 1, "Should have exactly one done event"
        assert "message_id" in done_events[0]

    @pytest.mark.asyncio
    async def test_message_persistence(self, client: AsyncClient):
        """Messages should be saved to DB and retrievable via /chat/history."""
        token = await register_and_login(client)

        sess_resp = await client.post(
            "/sessions",
            json={"name": "Persistence Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        session_id = sess_resp.json()["id"]

        # Send a message
        await client.post(
            "/chat",
            json={"session_id": session_id, "message": "I'm looking for medspas"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Retrieve history
        hist_resp = await client.get(
            f"/chat/history/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert hist_resp.status_code == 200
        history = hist_resp.json()

        roles = [m["role"] for m in history]
        assert "user" in roles
        assert "assistant" in roles

        user_msgs = [m for m in history if m["role"] == "user"]
        assert user_msgs[0]["content"] == "I'm looking for medspas"

    @pytest.mark.asyncio
    async def test_history_loads_on_second_message(self, client: AsyncClient):
        """Sending two messages should accumulate history."""
        token = await register_and_login(client)

        sess_resp = await client.post(
            "/sessions",
            json={"name": "History Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        session_id = sess_resp.json()["id"]

        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/chat", json={"session_id": session_id, "message": "Hello"}, headers=headers)
        await client.post("/chat", json={"session_id": session_id, "message": "I want Austin medspas"}, headers=headers)

        hist_resp = await client.get(f"/chat/history/{session_id}", headers=headers)
        history = hist_resp.json()

        assert len(history) == 4  # 2 user + 2 assistant messages

    @pytest.mark.asyncio
    async def test_history_forbidden_for_other_user(self, client: AsyncClient):
        """Users cannot see other users' chat history."""
        token1 = await register_and_login(client)

        # Register second user
        await client.post("/auth/register", json={
            "email": "other@example.com",
            "password": "testpass123",
        })
        resp2 = await client.post("/auth/login", json={
            "email": "other@example.com",
            "password": "testpass123",
        })
        token2 = resp2.json()["access_token"]

        # User1 creates session
        sess_resp = await client.post(
            "/sessions",
            json={"name": "Private Session"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        session_id = sess_resp.json()["id"]

        # User2 tries to read history — should 404
        hist_resp = await client.get(
            f"/chat/history/{session_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert hist_resp.status_code == 404
