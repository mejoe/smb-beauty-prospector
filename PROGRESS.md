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

## Sprint 2: AI Chat + Session ✅ COMPLETE
**Date:** 2026-03-02

### What Was Built

#### Backend
- **`POST /chat`** — full Claude SSE streaming endpoint
  - `StreamingResponse` with `text/event-stream` content type
  - Emits `{"type": "token", "text": "..."}` events per chunk
  - Emits `{"type": "done", "message_id": "...", "search_config": {...}, "job_id": "..."}` on finish
  - Emits `{"type": "error", "message": "..."}` on exception
  - Graceful stub mode when `ANTHROPIC_API_KEY` is not set — exercises full SSE pipeline with canned response
- **Conversation history** — loads full `chat_messages` table for session on every request; passes to Claude as messages array
- **Message persistence** — user message and assistant response both saved to `chat_messages`
- **`<search_config>` detection** — `extract_search_config()` regex parses XML-style block, validates JSON inside
  - If found: updates `session.search_config`, creates `EnrichmentJob` stub (status=queued), emits job_id in done event
- System prompt exactly per spec (B2B prospecting assistant for beauty/aesthetics)

#### Frontend
- **Two-panel layout** — left: streaming chat, right: search config card
- **Native `fetch` + SSE parsing** — replaces axios mutation; reads SSE stream token by token
- **Live streaming display** — assistant response builds in-place as tokens arrive (react-markdown rendered)
- **Search config preview card** — shows industries, geographies, target roles, filters as styled tag pills
- **"Launch Search" button** — enabled once `search_config` detected; calls `POST /companies/search`
- **Job status polling** — right panel polls `/jobs/{id}` every 3s and shows running/complete/failed badge
- History restoration — on page load, restores `search_config` from last assistant message with metadata

#### Tests (new — `tests/test_chat.py`, 11 tests)
- `extract_search_config` unit tests: valid block, no block, invalid JSON, full config, whitespace
- Integration: auth required, unknown session, stub SSE streaming, message persistence, history accumulation, cross-user isolation

### Test Results
```
25 passed, 0 failed in 12.47s
(14 Sprint 1 + 11 Sprint 2)
```

### Key Decisions / Notes
- `anthropic` library installed directly into venv site-packages (venv has no pip binary)
- `aiosqlite` also installed same way (needed for test isolation)
- Stub mode returns chunked canned response — ensures SSE pipeline works without API key
- Used native `fetch` in frontend for streaming (axios doesn't support streaming in browser)

---

## Sprint 3: Company Discovery ✅ COMPLETE
**Date:** 2026-03-02

### What Was Built

#### Backend
- **`POST /companies/search`** — triggers discovery from session's `search_config`
  - Verifies session ownership
  - Creates `EnrichmentJob` (entity_type="session", status=running)
  - Fires Celery task `discover_companies`; graceful fallback if Celery offline
- **`tasks.discover_companies` Celery task** (fully wired, realistic stubs)
  - STUB Google Places API — `GOOGLE_PLACES_API_KEY` env var to enable real calls
  - STUB Yelp Fusion API — `YELP_API_KEY` env var to enable real calls
  - Merge + dedup by `name_normalized` + city
  - Stores results in `companies` table, updates job status to complete
- **`GET /companies`** — enhanced with `state` and `has_linkedin` filters
- **`GET /companies/{id}`** — returns `CompanyDetailResponse` with `contact_count`
- **`POST /companies/import`** — bulk CSV import
  - Flexible column mapping (handles any reasonable CSV header names)
  - Deduplication by name_normalized + city
  - CSV injection prevention (strips leading `= + - @`)
  - 5MB file size cap; BOM-aware (utf-8-sig)
- **`GET /companies/export`** — CSV export with filters, CSV injection safe
- **`Company` model** — added `linkedin_url` field
- **`CompanyDetailResponse`** schema with `contact_count`, `last_enriched_at`, etc.

#### Seed Script
- `backend/scripts/seed_companies.py` — imports all 100 companies from `companies.csv`
  - Creates seed user if not found
  - Deduplicates against existing DB entries
  - Usage: `python scripts/seed_companies.py [--user-email X] [--csv path]`

#### Frontend (`Companies.tsx`)
- **TanStack Table** with sortable columns: name, city, state, industry, instagram, contacts, status
- **Filter bar**: city (text input), industry (select), has_instagram (yes/no/all)
- **Row click → company detail drawer** (slide-in panel with all fields + contact count)
- **"Import CSV" button** — file picker, calls `POST /companies/import`, shows toast
- **"Discover More" button** — calls search from active session's `search_config`, shows toast
- **"Export CSV" button** — downloads filtered CSV from server
- Added `import` and `export` methods to `companiesApi` in `api.ts`

#### Tests (`tests/test_companies.py`, 18 new tests)
- CRUD: create, list, get detail, update, delete, 404 handling
- Filters: city, state, has_instagram, pagination (non-overlapping pages)
- CSV import: happy path (3 companies), deduplication, non-CSV rejection
- CSV export: content verification, filter-aware export
- Search: invalid session → 404, valid session → job created
- Auth: unauthenticated access → 401

### Test Results
```
43 passed, 0 failed in 21.62s
(9 Sprint 1 auth + 5 Sprint 1 sessions + 11 Sprint 2 chat + 18 Sprint 3 companies)
```

### Security Review
- ✅ SQL injection: all queries use SQLAlchemy ORM with bound params
- ✅ CSV injection: `sanitize_csv_field()` strips `= + - @` prefixes in export
- ✅ Pagination: `ge=0` offset, `ge=1 le=500` limit constraints
- ✅ File size limit: 5MB cap on CSV import
- ✅ Session ownership: search endpoint verifies session belongs to current user
- ✅ Data isolation: all queries filter by `user_id`

### Key Decisions / Notes
- Discovery task uses sync SQLAlchemy (not async) — Celery workers don't use asyncio
- `linkedin_url` added to Company model (no migration needed — SQLite tests use `create_all`)
- Export uses streaming response to handle large datasets
- Stub data is realistic SA/ATX medspa data matching the real CSV format

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
