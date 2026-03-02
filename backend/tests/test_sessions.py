"""Tests for research sessions CRUD."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def client_with_auth():
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        reg = await c.post("/auth/register", json={"email": "sess@example.com", "password": "password123"})
        token = reg.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_session(client_with_auth):
    resp = await client_with_auth.post("/sessions", json={"name": "Austin Research", "description": "Test run"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Austin Research"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_sessions(client_with_auth):
    await client_with_auth.post("/sessions", json={"name": "Session A"})
    await client_with_auth.post("/sessions", json={"name": "Session B"})
    resp = await client_with_auth.get("/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_session(client_with_auth):
    create = await client_with_auth.post("/sessions", json={"name": "Get Me"})
    session_id = create.json()["id"]
    resp = await client_with_auth.get(f"/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Get Me"


@pytest.mark.asyncio
async def test_update_session(client_with_auth):
    create = await client_with_auth.post("/sessions", json={"name": "Old Name"})
    session_id = create.json()["id"]
    resp = await client_with_auth.put(f"/sessions/{session_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_session(client_with_auth):
    create = await client_with_auth.post("/sessions", json={"name": "Delete Me"})
    session_id = create.json()["id"]
    resp = await client_with_auth.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204
    resp2 = await client_with_auth.get(f"/sessions/{session_id}")
    assert resp2.status_code == 404
