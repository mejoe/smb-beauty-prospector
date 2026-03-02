"""
Tests for contacts endpoints - Sprint 4.
Covers: CRUD, CSV import, CSV export, pagination, filters, discover endpoint.
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
    resp = await client.post("/auth/register", json={
        "email": "contacts_test@example.com",
        "password": "password123",
        "name": "Test User",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_contact(auth_client):
    resp = await auth_client.post("/contacts", json={
        "name": "Ashley Johnson",
        "role": "Owner",
        "email": "ashley@luxespa.com",
        "instagram_handle": "ashley_luxe",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ashley Johnson"
    assert data["role"] == "Owner"
    assert data["instagram_handle"] == "ashley_luxe"
    assert data["enrichment_status"] == "pending"


@pytest.mark.asyncio
async def test_list_contacts(auth_client):
    for i in range(3):
        await auth_client.post("/contacts", json={"name": f"Contact {i}", "role": "Esthetician"})

    resp = await auth_client.get("/contacts")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_get_contact_detail(auth_client):
    create = await auth_client.post("/contacts", json={"name": "Detail Contact"})
    contact_id = create.json()["id"]

    resp = await auth_client.get(f"/contacts/{contact_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Contact"


@pytest.mark.asyncio
async def test_get_contact_not_found(auth_client):
    resp = await auth_client.get("/contacts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_contact(auth_client):
    create = await auth_client.post("/contacts", json={"name": "Old Name"})
    contact_id = create.json()["id"]

    resp = await auth_client.put(f"/contacts/{contact_id}", json={"name": "New Name", "status": "contacted"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["status"] == "contacted"


@pytest.mark.asyncio
async def test_delete_contact(auth_client):
    create = await auth_client.post("/contacts", json={"name": "To Delete"})
    contact_id = create.json()["id"]

    resp = await auth_client.delete(f"/contacts/{contact_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/contacts/{contact_id}")
    assert resp.status_code == 404


# ─── FILTERS ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_has_email(auth_client):
    await auth_client.post("/contacts", json={"name": "No Email"})
    await auth_client.post("/contacts", json={"name": "Has Email", "email": "test@example.com"})

    resp = await auth_client.get("/contacts?has_email=true")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["email"] == "test@example.com"

    resp2 = await auth_client.get("/contacts?has_email=false")
    assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_filter_has_instagram(auth_client):
    await auth_client.post("/contacts", json={"name": "No IG"})
    await auth_client.post("/contacts", json={"name": "Has IG", "instagram_handle": "igtest"})

    resp = await auth_client.get("/contacts?has_instagram=true")
    assert len(resp.json()) == 1

    resp2 = await auth_client.get("/contacts?has_instagram=false")
    assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_filter_has_linkedin(auth_client):
    await auth_client.post("/contacts", json={"name": "No LinkedIn"})
    await auth_client.post("/contacts", json={
        "name": "Has LinkedIn",
        "linkedin_url": "https://linkedin.com/in/test"
    })

    resp = await auth_client.get("/contacts?has_linkedin=true")
    assert len(resp.json()) == 1

    resp2 = await auth_client.get("/contacts?has_linkedin=false")
    assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_filter_by_title(auth_client):
    await auth_client.post("/contacts", json={"name": "Owner Person", "role": "Owner"})
    await auth_client.post("/contacts", json={"name": "Nurse Person", "role": "Nurse Injector"})

    resp = await auth_client.get("/contacts?title=nurse")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert "Nurse" in resp.json()[0]["role"]


@pytest.mark.asyncio
async def test_filter_by_company_id(auth_client):
    # Create a company
    company_resp = await auth_client.post("/companies", json={"name": "Test Spa", "city": "Austin"})
    company_id = company_resp.json()["id"]

    await auth_client.post("/contacts", json={"name": "Spa Staff", "company_id": company_id})
    await auth_client.post("/contacts", json={"name": "Unaffiliated"})

    resp = await auth_client.get(f"/contacts?company_id={company_id}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["company_id"] == company_id


@pytest.mark.asyncio
async def test_pagination(auth_client):
    for i in range(10):
        await auth_client.post("/contacts", json={"name": f"Paginate Contact {i}"})

    resp1 = await auth_client.get("/contacts?limit=5&offset=0")
    resp2 = await auth_client.get("/contacts?limit=5&offset=5")

    assert len(resp1.json()) == 5
    assert len(resp2.json()) == 5

    ids1 = {c["id"] for c in resp1.json()}
    ids2 = {c["id"] for c in resp2.json()}
    assert ids1.isdisjoint(ids2)


# ─── CSV IMPORT ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_import_csv(auth_client):
    csv_content = (
        "Contact Name,Role,Credentials,Business Name,Email,LinkedIn,Instagram,Source\n"
        "Ashley Johnson,Owner,LE,Luxe Spa,ashley@luxespa.com,,@ashley_luxe,website\n"
        "Jennifer Smith,Nurse Injector,RN,Glow Clinic,jen@glow.com,https://linkedin.com/in/jen,,yelp\n"
        "Rachel Davis,Esthetician,,,,,@racheld,\n"
    )
    file = io.BytesIO(csv_content.encode())
    resp = await auth_client.post(
        "/contacts/import",
        files={"file": ("contacts.csv", file, "text/csv")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] == 3
    assert data["skipped"] == 0

    resp2 = await auth_client.get("/contacts")
    assert len(resp2.json()) == 3


@pytest.mark.asyncio
async def test_import_csv_dedup(auth_client):
    """Importing same CSV twice skips duplicates on second pass."""
    csv_content = "Contact Name,Role\nAshley Dedup,Owner\n"
    file = io.BytesIO(csv_content.encode())
    await auth_client.post("/contacts/import", files={"file": ("c.csv", file, "text/csv")})

    file2 = io.BytesIO(csv_content.encode())
    resp = await auth_client.post("/contacts/import", files={"file": ("c.csv", file2, "text/csv")})
    assert resp.json()["imported"] == 0
    assert resp.json()["skipped"] == 1


@pytest.mark.asyncio
async def test_import_non_csv_rejected(auth_client):
    file = io.BytesIO(b"not a csv")
    resp = await auth_client.post(
        "/contacts/import",
        files={"file": ("data.txt", file, "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_strips_instagram_at(auth_client):
    """Instagram handles with @ prefix should be stored without it."""
    csv_content = "Contact Name,Instagram\nIG Test,@myhandle\n"
    file = io.BytesIO(csv_content.encode())
    await auth_client.post("/contacts/import", files={"file": ("c.csv", file, "text/csv")})

    resp = await auth_client.get("/contacts")
    assert resp.json()[0]["instagram_handle"] == "myhandle"


# ─── CSV EXPORT ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_csv(auth_client):
    await auth_client.post("/contacts", json={
        "name": "Export Contact",
        "role": "Owner",
        "email": "export@example.com",
        "instagram_handle": "exportig",
    })

    resp = await auth_client.get("/contacts/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    text = resp.text
    assert "Export Contact" in text
    assert "export@example.com" in text
    assert "@exportig" in text


@pytest.mark.asyncio
async def test_export_csv_filtered(auth_client):
    await auth_client.post("/contacts", json={"name": "With Email", "email": "a@b.com"})
    await auth_client.post("/contacts", json={"name": "No Email"})

    resp = await auth_client.get("/contacts/export?has_email=true")
    assert resp.status_code == 200
    text = resp.text
    assert "With Email" in text
    assert "No Email" not in text


@pytest.mark.asyncio
async def test_export_csv_empty(auth_client):
    """Empty export should still return valid CSV with headers."""
    resp = await auth_client.get("/contacts/export")
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) == 1  # just headers
    assert "Name" in lines[0]


# ─── DISCOVER ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discover_contacts_invalid_company(auth_client):
    resp = await auth_client.post("/contacts/discover/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_discover_contacts_queues_job(auth_client):
    """Discover endpoint should create a job (Celery may not be running in test)."""
    company_resp = await auth_client.post("/companies", json={"name": "Test Discovery Spa", "city": "Austin"})
    company_id = company_resp.json()["id"]

    resp = await auth_client.post(f"/contacts/discover/{company_id}")
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["company_id"] == company_id


# ─── ENRICH ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enrich_contact(auth_client):
    create = await auth_client.post("/contacts", json={"name": "Enrich Me"})
    contact_id = create.json()["id"]

    resp = await auth_client.post(f"/contacts/{contact_id}/enrich")
    assert resp.status_code == 202
    assert "job_id" in resp.json()


@pytest.mark.asyncio
async def test_enrich_nonexistent_contact(auth_client):
    resp = await auth_client.post("/contacts/00000000-0000-0000-0000-000000000000/enrich")
    assert resp.status_code == 404


# ─── AUTH CHECKS ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_list(client):
    resp = await client.get("/contacts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_export(client):
    resp = await client.get("/contacts/export")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_import(client):
    file = io.BytesIO(b"Contact Name\nTest\n")
    resp = await client.post("/contacts/import", files={"file": ("c.csv", file, "text/csv")})
    assert resp.status_code == 401
