Purpose
-------
This file gives focused, actionable guidance to AI coding agents working on the Utah Watchdog repo. It highlights the architecture, run/test workflows, and project-specific conventions you must follow to be immediately productive.

Quick wins
----------
- Environment: create a `.env` in the repo root with `MONGODB_URI`, `MONGODB_DATABASE`, and `CONGRESS_GOV_API_KEY` (see [src/config/settings.py](src/config/settings.py#L1-L40)).
- Sanity checks: run the built-in tests before touching ingestion or UI code:

```bash
python scripts/test_connection.py
```

Architecture (big picture)
--------------------------
- Data ingestion pipelines (async) live in `src/ingestion/` and follow an ETL pattern implemented by `BaseIngester` ([src/ingestion/base.py](src/ingestion/base.py#L1-L40)).
- Pydantic models live in `src/models/` and are the canonical schema used by `transform()` functions.
- MongoDB is the single source-of-truth; both sync scripts and async services write/read it. Connection helpers are in [src/database/connection.py](src/database/connection.py#L1-L40).
- UI: a Streamlit frontend is in `frontend/app.py` and uses the synchronous client (cached) to read collections directly.
- Intended API surface: `fastapi` is a declared dependency (pyproject), but `src/api/__init__.py` is empty; agents should search for or create FastAPI app entrypoints when adding backend routes.

Run / developer workflows
------------------------
- Basic validation of credentials and DB: `python scripts/test_connection.py` (verifies `.env`, Mongo, and Congress.gov key).
- Populate politicians: `python scripts/sync_members.py` (uses `CongressMembersIngester`). See usage and flags in [scripts/sync_members.py](scripts/sync_members.py#L1-L40).
- Streamlit frontend: run with `streamlit run frontend/app.py` (reads DB synchronously). The app suggests using `python scripts/sync_members.py` to populate data.
- FastAPI (if implemented): run via `uvicorn` pointing at the app module; search repo for where `app` is defined. If missing, create `src/api/app.py` and expose `app: FastAPI`.

Key code patterns and conventions
------------------------------
- Ingestion contract (must follow):
  - `fetch_data(self, **kwargs) -> AsyncGenerator[dict, None]` — yield raw records. See [src/ingestion/congress_members.py](src/ingestion/congress_members.py#L1-L40).
  - `transform(self, raw: dict) -> Model` — return a Pydantic model from `src/models/`.
  - `load(self, item: Model) -> bool` — upsert into MongoDB and return True for insert, False for update. Ingesters should be idempotent (see `CongressMembersIngester.load`).
- Use async for ingestion and FastAPI. Scripts (CLI / Streamlit) typically use the synchronous client. `src/database/connection.py` exposes both `get_sync_client()` and `get_async_client()` — prefer them where applicable.
- Bulk DB writes: use `pymongo.UpdateOne` + `bulk_write` pattern for member votes (see [src/ingestion/votes.py](src/ingestion/votes.py#L1-L40)).
- Rate limiting: honor constants in [src/config/constants.py](src/config/constants.py#L1-L40) (e.g., `CONGRESS_GOV_RATE_LIMIT`, `RATE_LIMIT_DELAY`).

Integration points & external deps
---------------------------------
- MongoDB: connection string in `.env` → `settings.MONGODB_URI` and `settings.MONGODB_DATABASE` ([src/config/settings.py](src/config/settings.py#L1-L80)).
- Congress.gov API: `CONGRESS_GOV_API_KEY` used by ingestion code; validate with `scripts/test_connection.py`.
- Optional: `OPENAI_API_KEY` for embeddings/agents; settings contain `EMBEDDING_MODEL` and `AGENT_MODEL` configuration.

What to look for when changing/adding code
-----------------------------------------
- If you add an ingester: implement the ETL contract and write a small `scripts/` runner to allow manual syncs (pattern: `scripts/sync_members.py`).
- Prefer idempotent upserts and mark previous occupants as out-of-office where necessary (see `CongressMembersIngester.load`).
- If adding an API route, use async DB client from `src/database/connection.py` and prefer Motor (`AsyncIOMotorClient`) in endpoints.

Notes for AI agents
-------------------
- Focus on existing patterns; copy the `BaseIngester` flow rather than inventing a new pipeline shape.
- When proposing changes that affect runtime (new env vars, DB migrations, or scheduled tasks), include precise run commands and a minimal test script in `scripts/`.
- If the FastAPI app is missing, ask the maintainer whether to scaffold `src/api/app.py` or implement routes inside `src/api/`.

Where to start (first edit suggestions)
-------------------------------------
1. Create `.env.example` listing required env vars.
2. Add a minimal `src/api/app.py` (if APIs are needed) that imports the async DB client.
3. Improve README.md with run commands (the repo README is currently empty).

Feedback
--------
If any section is unclear or you'd like more examples (e.g., exact FastAPI scaffolding, example `.env.example`, or a sample ingester), tell me which piece to expand.
