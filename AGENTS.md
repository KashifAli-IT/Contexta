# AGENTS.md — Contexta Py agent runbook

## FIRST: read the build plan
Before any work, read `PLAN.md` in the repo root and check the §3 Progress Tracker.
Continue from the step after the last completed one (format `S<stage>.<step>`).
Do not redo completed stages. Record every deviation in `PLAN.md` §13 Decision Log.

## Repo layout
```
backend/    FastAPI + LangGraph service and Arq worker (Python 3.12, runs in Docker)
frontend/   Next.js 16 App Router UI (Node 24)
infra/      helper scripts mounted into containers (e.g. MinIO bucket bootstrap)
scripts/    developer + smoke-test scripts (PowerShell-friendly)
PLAN.md     master staged build plan (source of truth)
```

## Critical environment rules
- **Never create a host Python venv for the backend.** The host has Python 3.14/3.11 only;
  torch/onnxruntime/docling wheels are unavailable there. All backend work runs in
  `python:3.12-slim` containers.
- Docker Desktop lives at `C:\Users\USER\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe`
  (not the default Program Files path). Start it before any compose command.
- Shell is Windows PowerShell 5.1: **no `&&`**. Use `;` or separate calls.
- `.env` is git-ignored. Only `.env.example` is committed.

## Canonical commands
```powershell
# whole stack
docker compose --profile app up -d --build
docker compose --profile app logs -f api worker
docker compose down -v

# infra only
docker compose up -d postgres redis qdrant minio createbuckets

# backend one-offs (preferred over host tooling)
docker compose run --rm api alembic upgrade head
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api ruff format --check .
docker compose run --rm api mypy app
docker compose run --rm api python scripts/smoke_test.py

# frontend
cd frontend
npm ci
npm run dev
npm run lint
npm run build
```

## Definition of done per stage
1. All step IDs in the stage completed.
2. Stage acceptance criteria pass (command output pasted).
3. `PLAN.md` §3 stage row marked done; last step ID reported.
4. One commit for the stage using the exact message in the stage block.
   Never amend. Never combine two stages into one commit.

## Code conventions
- Python: ruff-formatted, line length 100, type hints on public functions,
  `async` for all I/O; wrap blocking calls in `asyncio.to_thread`.
- No blocking HTTP/LLM calls inside the event loop; use `asyncio.gather` for fan-out.
- Every FastAPI route declares `response_model` and explicit `status_code`.
- All API errors use the envelope `{"error": {"code", "message", "request_id"}}`.
- Frontend: TypeScript strict, no `any`, shadcn primitives for UI,
  `"use client"` only where interactivity requires it.
- Commits: `<type>(<scope>): <lowercase imperative summary>` with
  types `feat|fix|chore|test|docs|refactor|infra`.

## API surface (frontend must match exactly)
```
GET    /api/v1/health
GET    /api/v1/health/ready
POST   /api/v1/documents                       multipart -> 202 {job_id, document_id, status}
GET    /api/v1/documents?project_id=
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/file     302 -> presigned MinIO URL
POST   /api/v1/documents/{document_id}/retry    202
GET    /api/v1/documents/events                SSE document-status stream
POST   /api/v1/chat/stream                     SSE thought stream
GET    /api/v1/chat/history/{session_id}
DELETE /api/v1/chat/history/{session_id}
POST   /api/v1/tts                             audio/mpeg stream
GET    /api/v1/tts/voices
```

## SSE contract (both streams)
`Content-Type: text/event-stream`, `Cache-Control: no-cache`,
`X-Accel-Buffering: no`, frames `data: {json}\n\n`, `: ping` heartbeat every 15s.
Chat events: `agent_state {step,message}`, `citations {items}`, `token {content}`,
`error {message}`, `done {session_id,message_id}`.
Chat steps vocabulary: `routing, expanding, retrieval, reranking, grading,
generating, web_fallback, done`.
The browser client must use `fetch` streaming (see `frontend/src/lib/sse.ts`) —
`EventSource` cannot POST a JSON body.