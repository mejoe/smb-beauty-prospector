"""
Tests for Instagram enrichment endpoints - Sprint 5.
Covers: session management, health check, enrichment queue, bulk enrich.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


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
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client):
    resp = await client.post("/auth/register", json={
        "email": "ig_test@example.com",
        "password": "password123",
        "name": "Test User",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ─── Session Management ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_status_not_connected(auth_client):
    resp = await auth_client.get("/instagram/session-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["health"] == "missing"


@pytest.mark.asyncio
async def test_save_session(auth_client):
    resp = await auth_client.post("/instagram/session", json={
        "username": "testuser",
        "cookies_json": '{"sessionid": "abc123", "ds_user_id": "12345"}',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["username"] == "testuser"
    assert data["health"] == "ok"


@pytest.mark.asyncio
async def test_session_status_after_save(auth_client):
    await auth_client.post("/instagram/session", json={
        "username": "myaccount",
        "cookies_json": '{"sessionid": "xyz"}',
    })
    resp = await auth_client.get("/instagram/session-status")
    assert resp.status_code == 200
    assert resp.json()["connected"] is True
    assert resp.json()["username"] == "myaccount"


@pytest.mark.asyncio
async def test_delete_session(auth_client):
    await auth_client.post("/instagram/session", json={
        "username": "toDelete",
        "cookies_json": '{"sessionid": "abc"}',
    })
    resp = await auth_client.delete("/instagram/session")
    assert resp.status_code == 204

    resp2 = await auth_client.get("/instagram/session-status")
    assert resp2.json()["connected"] is False


@pytest.mark.asyncio
async def test_session_health_no_session(auth_client):
    resp = await auth_client.get("/instagram/session/health")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
    assert resp.json()["reason"] == "no_session"


@pytest.mark.asyncio
async def test_session_health_with_session(auth_client):
    await auth_client.post("/instagram/session", json={
        "username": "healthtest",
        "cookies_json": '{"sessionid": "valid123"}',
    })
    resp = await auth_client.get("/instagram/session/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["username"] == "healthtest"
    assert "rate_limit_info" in data
    assert data["rate_limit_info"]["max_profile_views_per_hour"] == 50


# ─── Enrichment Queue ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_queue_empty(auth_client):
    resp = await auth_client.get("/instagram/queue")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_enrich_contact(auth_client):
    create = await auth_client.post("/contacts", json={"name": "Ashley Test", "role": "Owner"})
    contact_id = create.json()["id"]

    resp = await auth_client.post(f"/instagram/enrich/{contact_id}")
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["contact_id"] == contact_id


@pytest.mark.asyncio
async def test_enrich_nonexistent_contact(auth_client):
    resp = await auth_client.post("/instagram/enrich/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_queue_shows_job_after_enrich(auth_client):
    create = await auth_client.post("/contacts", json={"name": "Queue Test Contact"})
    contact_id = create.json()["id"]

    await auth_client.post(f"/instagram/enrich/{contact_id}")

    resp = await auth_client.get("/instagram/queue")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["entity_id"] == contact_id
    assert jobs[0]["contact_name"] == "Queue Test Contact"


@pytest.mark.asyncio
async def test_bulk_enrich(auth_client):
    ids = []
    for i in range(3):
        c = await auth_client.post("/contacts", json={"name": f"Bulk Contact {i}"})
        ids.append(c.json()["id"])

    resp = await auth_client.post("/instagram/bulk-enrich", json={"contact_ids": ids})
    assert resp.status_code == 202
    data = resp.json()
    assert data["queued"] == 3
    assert len(data["job_ids"]) == 3


@pytest.mark.asyncio
async def test_bulk_enrich_filters_bad_ids(auth_client):
    """Bulk enrich should silently skip contacts that don't belong to user."""
    c = await auth_client.post("/contacts", json={"name": "Good Contact"})
    good_id = c.json()["id"]

    resp = await auth_client.post("/instagram/bulk-enrich", json={
        "contact_ids": [good_id, "00000000-0000-0000-0000-000000000001"]
    })
    assert resp.status_code == 202
    assert resp.json()["queued"] == 1


@pytest.mark.asyncio
async def test_enrich_all_pending(auth_client):
    for i in range(3):
        await auth_client.post("/contacts", json={"name": f"Pending Contact {i}"})

    resp = await auth_client.post("/instagram/enrich-all-pending")
    assert resp.status_code == 202
    assert resp.json()["queued"] == 3


@pytest.mark.asyncio
async def test_enrich_all_pending_skips_enriched(auth_client):
    """Contacts with instagram_handle already set should not be re-queued."""
    # Contact with IG already
    await auth_client.post("/contacts", json={
        "name": "Already Enriched",
        "instagram_handle": "already_has_ig",
    })
    # Pending contact
    await auth_client.post("/contacts", json={"name": "Still Pending"})

    resp = await auth_client.post("/instagram/enrich-all-pending")
    assert resp.status_code == 202
    # Only the pending one should be queued
    assert resp.json()["queued"] == 1


# ─── Auth Checks ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_queue(client):
    resp = await client.get("/instagram/queue")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_save_session(client):
    resp = await client.post("/instagram/session", json={
        "username": "x", "cookies_json": "{}"
    })
    assert resp.status_code == 401
