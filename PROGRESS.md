# BeautyProspector - Build Progress

## Sprint 1: Foundation ✅ COMPLETE
**Date:** 2026-03-02

### What Was Built

#### Backend (Python 3.12 + FastAPI + SQLAlchemy)
- **Full database schema** via SQLAlchemy async models:
  - `users` — auth, Instagram session storage (AES-256 encrypted)
  - `research_sessions` — scoped research workspaces
  - `companies` — discovered businesses with social/CRM fields
  - `contacts` — enrichment-ready contacts with IG/LinkedIn fields
  - `outreach_campaigns` + `outreach_messages` — DM broadcast system
  - `chat_messages` — AI chat history per session
  - `enrichment_jobs` — job queue tracking

- **Alembic migrations** configured (auto-generates from SQLAlchemy models)

- **JWT Auth** (register, login, refresh, logout, /me)
  - bcrypt password hashing
  - Access tokens (60min) + refresh tokens (30 days)
  - HTTPBearer scheme on all protected routes

- **AES-256 encryption** for Instagram session cookies via Fernet

- **Full REST API** with auth-protected routes:
  - `/auth/*` — register, login, refresh, logout, me
  - `/sessions/*` — CRUD for research sessions
  - `/companies/*` — CRUD + search trigger (stub)
  - `/contacts/*` — CRUD + enrich triggers (stub)
  - `/instagram/*` — session status, save, delete
  - `/outreach/campaigns/*` — CRUD + start/pause with confirmation gate
  - `/jobs/*` — enrichment job tracking
  - `/chat/*` — AI chat (stub for Sprint 2)
  - `/export/*` — CSV/Sheets (stub for Sprint 9)

- **Celery task stubs** for discovery, enrichment, outreach, export
  - DM send engine blocked behind `DEV_MODE = True` flag

- **CORS, error handling, health endpoint**

#### Frontend (React 18 + TypeScript + Tailwind)
- Vite scaffold with TypeScript
- React Router v6 with protected/public route guards
- AuthContext with JWT storage + auto-refresh interceptor
- TanStack Query for server state
- Pages built:
  - Login + Register (full form validation)
  - Dashboard (stats cards + quick actions)
  - Sessions (list/create/delete)
  - ChatSession (message UI, streaming-ready, stub backend)
  - Companies (filterable table)
  - Contacts (table with enrich action)
  - Outreach (campaign CRUD + **prominent confirmation modal** before send)
  - EnrichmentQueue (live polling table)
  - Settings (Instagram connect + account info)
- Layout with sidebar navigation
- Tailwind brand color (pink/brand-500 = #ec4899)
- API client (`src/lib/api.ts`) with all endpoints mapped

#### Infrastructure
- `docker-compose.yml` with: api, worker, db (Postgres 16), redis
- `Dockerfile` for backend (python:3.12-slim)
- `Dockerfile` + `nginx.conf` for frontend (node build → nginx SPA)

### Test Results
```
14 passed, 0 failed in 6.47s

Tests:
- test_auth.py: register, duplicate_email, weak_password, login, wrong_password, me, refresh_token, unauthorized_access, health
- test_sessions.py: create, list, get, update, delete
```

Test infrastructure: pytest + pytest-asyncio + httpx AsyncClient + aiosqlite in-memory DB
Custom `JSONBCompat` type handles PostgreSQL JSONB → SQLite JSON for tests.

### Key Decisions
1. `JSONBCompat` custom SQLAlchemy type — allows JSONB in production, JSON in SQLite tests
2. `metadata` column renamed to `msg_metadata` (SQLAlchemy reserved name)
3. Pydantic v2 `model_config` dict pattern used throughout
4. Outreach confirmation gate: both API (`⚠️` comment) and UI modal
5. DM send blocked in code: `DEV_MODE = True` in `tasks/outreach.py`

### Issues / Notes
- No `pip` or `venv` on host by default; installed via `get-pip.py --break-system-packages`
- Node `npm create vite` has interactive prompts that don't work headlessly; scaffolded manually
- `psycopg2-binary` included but tests use aiosqlite; Postgres needed for production

---

## Sprint 2: AI Chat + Session
**Status:** 🔜 NEXT

**Plan:**
- Implement `POST /chat` with Claude SSE streaming (using `anthropic` SDK)
- Chat message persistence with history loading
- `<search_config>` block detection → update session config
- Frontend: upgrade ChatSession.tsx to parse SSE stream
- Frontend: Search config preview card in session layout

**Prerequisite:** `pip install anthropic` (already in requirements.txt)

---

## Sprint 3: Company Discovery Engine
**Status:** 📋 PLANNED
- Google Places API (stub with mock data, env var: `GOOGLE_PLACES_API_KEY`)
- Yelp Fusion API (stub with mock data, env var: `YELP_API_KEY`)
- SerpAPI (stub with mock data, env var: `SERP_API_KEY`)
- Instagram hashtag discovery (Playwright, uses IG session)
- Deduplication logic

---

## Sprint 4: Contact Discovery
**Status:** 📋 PLANNED
- Playwright website staff crawler
- Claude staff extraction prompt
- Yelp review mining

---

## Sprint 5: Instagram Enrichment (PRIORITY - REAL IMPLEMENTATION)
**Status:** 📋 PLANNED
- Method A: Follower scrape + fuzzy name match (thefuzz)
- Method B: IG name search + composite scoring
- Method C: Hashtag cross-reference
- Rate limiting (50 profile views/hr, 2-5s delays)
- Instagram session management with health checks

---

## Sprint 6-9: LinkedIn, CRM, Outreach, Export
**Status:** 📋 PLANNED

---

## Seed Data
Located at: `/home/joemcbride/.openclaw/workspace/company-docs/medspa-market-research/`
- `master_contacts_clean.csv` — 646 contacts
- `companies.csv` — 100 companies

**Import planned for Sprint 9** as session "Austin + San Antonio - Initial Research 2026"
