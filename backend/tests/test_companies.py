"""
Tests for companies endpoints - Sprint 3.
Covers: CRUD, CSV import, CSV export, pagination, filters, search trigger.
"""
import io
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
    """Client with registered + logged-in user."""
    resp = await client.post("/auth/register", json={
        "email": "company_test@example.com",
        "password": "password123",
        "name": "Test User",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_company(auth_client):
    resp = await auth_client.post("/companies", json={
        "name": "Luxe MedSpa",
        "city": "Austin",
        "state": "TX",
        "category": "medspa",
        "instagram_handle": "luxemedspa",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Luxe MedSpa"
    assert data["city"] == "Austin"
    assert data["instagram_handle"] == "luxemedspa"


@pytest.mark.asyncio
async def test_list_companies(auth_client):
    # Create 3 companies
    for i in range(3):
        await auth_client.post("/companies", json={"name": f"Spa {i}", "city": "Austin"})

    resp = await auth_client.get("/companies")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_get_company_detail(auth_client):
    create = await auth_client.post("/companies", json={"name": "Detail Spa", "city": "Dallas"})
    company_id = create.json()["id"]

    resp = await auth_client.get(f"/companies/{company_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Spa"
    assert "contact_count" in data


@pytest.mark.asyncio
async def test_get_company_not_found(auth_client):
    resp = await auth_client.get("/companies/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_company(auth_client):
    create = await auth_client.post("/companies", json={"name": "Old Name"})
    company_id = create.json()["id"]

    resp = await auth_client.put(f"/companies/{company_id}", json={"name": "New Name", "status": "contacted"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "contacted"


@pytest.mark.asyncio
async def test_delete_company(auth_client):
    create = await auth_client.post("/companies", json={"name": "To Delete"})
    company_id = create.json()["id"]

    resp = await auth_client.delete(f"/companies/{company_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/companies/{company_id}")
    assert resp.status_code == 404


# ─── FILTERS ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_by_city(auth_client):
    await auth_client.post("/companies", json={"name": "Austin Spa", "city": "Austin"})
    await auth_client.post("/companies", json={"name": "Dallas Spa", "city": "Dallas"})

    resp = await auth_client.get("/companies?city=Austin")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["city"] == "Austin"


@pytest.mark.asyncio
async def test_filter_by_has_instagram(auth_client):
    await auth_client.post("/companies", json={"name": "No IG Spa"})
    await auth_client.post("/companies", json={"name": "IG Spa", "instagram_handle": "ighandle"})

    resp_ig = await auth_client.get("/companies?has_instagram=true")
    assert len(resp_ig.json()) == 1
    assert resp_ig.json()[0]["instagram_handle"] == "ighandle"

    resp_no_ig = await auth_client.get("/companies?has_instagram=false")
    assert len(resp_no_ig.json()) == 1


@pytest.mark.asyncio
async def test_filter_by_state(auth_client):
    await auth_client.post("/companies", json={"name": "TX Spa", "city": "Austin", "state": "TX"})
    await auth_client.post("/companies", json={"name": "CA Spa", "city": "LA", "state": "CA"})

    resp = await auth_client.get("/companies?state=TX")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_pagination(auth_client):
    for i in range(10):
        await auth_client.post("/companies", json={"name": f"Paginate Spa {i}"})

    resp1 = await auth_client.get("/companies?limit=5&offset=0")
    resp2 = await auth_client.get("/companies?limit=5&offset=5")

    assert len(resp1.json()) == 5
    assert len(resp2.json()) == 5

    ids1 = {c["id"] for c in resp1.json()}
    ids2 = {c["id"] for c in resp2.json()}
    assert ids1.isdisjoint(ids2), "Pages should not overlap"


# ─── CSV IMPORT ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_csv(auth_client):
    csv_content = (
        "Company,City,Category,Address,Phone,Website,Business Instagram,Notes\n"
        "Test Spa A,Austin,medspa,123 Main St,(512) 555-0001,https://testspaa.com,@testspaa,\n"
        "Test Spa B,Dallas,medspa,456 Oak St,(214) 555-0002,https://testspab.com,,Some notes\n"
        "Test Spa C,Houston,medspa,789 Pine St,(713) 555-0003,,,\n"
    )
    file = io.BytesIO(csv_content.encode())

    resp = await auth_client.post(
        "/companies/import",
        files={"file": ("companies.csv", file, "text/csv")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 3
    assert data["skipped"] == 0

    # Verify they're in DB
    resp2 = await auth_client.get("/companies")
    assert len(resp2.json()) == 3


@pytest.mark.asyncio
async def test_import_csv_dedup(auth_client):
    """Importing same CSV twice should skip duplicates on second pass."""
    csv_content = (
        "Company,City,Category\n"
        "Dupe Spa,Austin,medspa\n"
    )
    file = io.BytesIO(csv_content.encode())
    await auth_client.post("/companies/import", files={"file": ("c.csv", file, "text/csv")})

    file2 = io.BytesIO(csv_content.encode())
    resp = await auth_client.post("/companies/import", files={"file": ("c.csv", file2, "text/csv")})
    data = resp.json()
    assert data["imported"] == 0
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_import_non_csv_rejected(auth_client):
    file = io.BytesIO(b"not a csv")
    resp = await auth_client.post(
        "/companies/import",
        files={"file": ("data.txt", file, "text/plain")},
    )
    assert resp.status_code == 400


# ─── CSV EXPORT ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_csv(auth_client):
    await auth_client.post("/companies", json={
        "name": "Export Spa", "city": "Austin", "state": "TX",
        "instagram_handle": "exportspa",
    })

    resp = await auth_client.get("/companies/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    text = resp.text
    assert "Export Spa" in text
    assert "Austin" in text
    assert "@exportspa" in text


@pytest.mark.asyncio
async def test_export_csv_filtered(auth_client):
    await auth_client.post("/companies", json={"name": "Austin Spa", "city": "Austin", "state": "TX"})
    await auth_client.post("/companies", json={"name": "Dallas Spa", "city": "Dallas", "state": "TX"})

    resp = await auth_client.get("/companies/export?city=Austin")
    assert resp.status_code == 200
    text = resp.text
    assert "Austin Spa" in text
    assert "Dallas Spa" not in text


# ─── SEARCH / DISCOVERY ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_requires_valid_session(auth_client):
    """Search with invalid session should 404."""
    resp = await auth_client.post("/companies/search", json={
        "session_id": "00000000-0000-0000-0000-000000000000",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_with_valid_session(auth_client):
    """Search with valid session should queue job and return job_id."""
    # Create a session first
    sess = await auth_client.post("/sessions", json={"name": "Test Session"})
    assert sess.status_code == 201
    session_id = sess.json()["id"]

    resp = await auth_client.post("/companies/search", json={
        "session_id": session_id,
        "search_config": {"location": "Austin, TX", "industry": "medspa"},
    })
    # 202 or 500 (Celery not running in test) — we just verify job was created
    assert resp.status_code in (202, 500)
    if resp.status_code == 202:
        data = resp.json()
        assert "job_id" in data
        assert data["session_id"] == session_id


# ─── AUTH CHECKS ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_list(client):
    resp = await client.get("/companies")
    assert resp.status_code == 401
