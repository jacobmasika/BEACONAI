# BeaconAI

BeaconAI is an offline-first search-and-rescue system for missing persons using local inference in JavaScript and agentic matching in Python.

## What This Implements

- On-device feature embedding in the frontend using Transformers.js
- Offline queueing on client using IndexedDB for low/no connectivity
- Flask backend with required routes:
  - `POST /api/sighting`
  - `GET /api/matches`
  - `POST /api/public/cases`
  - `GET /api/public/cases`
  - `POST /api/search/missing`
- PostgreSQL + pgvector for vector similarity search
- SQLite fallback queue on backend for resilience
- Agentic match action hooks for guardian notification and law enforcement handoff payload generation
- Responsible AI safeguards: embeddings are stored, raw images are not persisted

## Architecture

1. Frontend captures an image and text context.
2. Frontend generates a local embedding via Transformers.js.
3. If offline, sighting is queued in IndexedDB.
4. When online, sighting is sent to Flask API.
5. Backend stores vector in PostgreSQL and runs nearest-neighbor match against missing-person vectors.
6. If similarity is above threshold (default `0.85`), the system triggers guardian notification and marks the record for law enforcement handoff.

## Setup

### One-Command Dev Startup (Windows PowerShell)

```powershell
./scripts/dev-up.ps1
```

This script starts local pgvector PostgreSQL (Docker), installs backend dependencies, and launches backend/frontend servers.

### No-Docker Startup (Hosted Postgres + pgvector)

If Docker Desktop is unstable on your machine, use a hosted Postgres instance with pgvector (for example Supabase or Neon), then run:

```powershell
./scripts/dev-up.ps1 -SkipDocker
```

In this mode, BeaconAI uses `DATABASE_URL` from `backend/.env`.

### 1) Start PostgreSQL + pgvector

```bash
cd infra
docker compose up -d
```

### 2) Configure Backend

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

### 3) Run Backend

```bash
cd backend
python run.py
```

Backend runs on `http://localhost:5000`.

### 4) Run Frontend

Use any static server. Example with Python:

```bash
cd frontend
python -m http.server 8080
```

Open `http://localhost:8080`.

## Tests

Run backend unit tests:

```powershell
./scripts/dev-test.ps1
```

## API Contract

### POST /api/sighting

Request JSON:

```json
{
  "source_device_id": "field-unit-7",
  "description": "Child, green shirt near bus stop",
  "captured_at_iso": "2026-03-24T11:20:00Z",
  "location": {"lat": 0, "lng": 0},
  "embedding": [0.01, 0.02]
}
```

Response includes status and match metadata.

### GET /api/matches

Returns recent matched sightings.

### POST /api/public/cases

Public intake endpoint for family/friends to submit missing person cases.

### GET /api/public/cases

Returns recent public missing-person reports.

### POST /api/search/missing

AI-enhanced missing-person search using description and/or embedding vector.

## Responsible AI Notes

- Raw facial images are processed locally in the browser and are not stored by the backend.
- Backend stores only embeddings and metadata needed for search-and-rescue workflows.
- API keys and cloud credentials are loaded from environment variables only.

## Future Integrations

- Azure AI Foundry agent orchestration for richer case triage
- Government/Law Enforcement API handoff at `LAW_ENFORCEMENT_API_BASE_URL`
- Azure AI Toolkit workflows in VS Code for model and prompt iteration

## Deploy on Vercel (Serverless)

This repository is configured for Vercel serverless deployment:

- API entrypoint: `api/index.py`
- Static frontend: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`
- Routing: `vercel.json`

### 1) Push to GitHub

Push this repository to GitHub and import it in Vercel.

### 2) Configure Environment Variables in Vercel

Set at minimum:

- `DATABASE_URL` = managed PostgreSQL + pgvector connection string

Optional tuning:

- `VECTOR_DIMENSIONS` (default `512`)
- `SIMILARITY_THRESHOLD` (default `0.85`)
- `IMAGE_SEARCH_MIN_SIMILARITY` (default `0.55`)

### 3) Recommended Production Database

Use a hosted PostgreSQL instance with pgvector enabled (for example Neon or Supabase).

### 4) Notes

- Vercel filesystem is ephemeral/read-only except `/tmp`.
- Authoritative app data requires managed PostgreSQL + pgvector on Vercel. If `DATABASE_URL` is missing or invalid, API endpoints return `503` with guidance.
- Vercel provider URLs like `postgresql://...` and `postgres://...` are normalized to `postgresql+psycopg://...` automatically.

## Hackathon Assets
- Submission checklist: `docs/hackathon/submission-checklist.md`
- Blog draft template: `docs/hackathon/blog-draft.md`
- Demo script (3-5 min): `docs/hackathon/demo-script.md`
- Submission form copy pack: `docs/hackathon/submission-form-pack.md`

