# Contexta Py — Master Build Plan

> **This file is the single source of truth for the build.** It is fully self-contained:
> start a new chat, paste this file + the last completed step ID (e.g. `S05.07`), and the
> build continues with zero missing context.

---

## 0. How To Use This Plan

### 0.1 Resume Protocol
1. Read this `PLAN.md` from the repo root (or paste it into the new session).
2. State the **last completed step ID** — format `S<stage>.<step>`, e.g. `S04.03`.
3. State any open issue from §13 that was mid-flight.
4. Resume at the next step after that ID, sequentially, committing at every stage boundary.

### 0.2 Step ID Format
- `S01.01` = Stage 1, Step 1. Every actionable step has an ID.
- `⛔ DECISION` — a choice is required; a default is given so it can be auto-proceed.
- `⚠ RISK` — may fail; mitigation is inline.
- `✔ CHECK` — has a verification command.

### 0.3 Per-Stage Workflow (mandatory)
Each stage ends with the same 4 beats:
1. **Implement** the steps.
2. **Verify** the stage's `✔ Acceptance Criteria`.
3. **Report progress** — list completed step IDs and mark the stage `✅` in §3.
4. **Commit** — `git add -A` then `git commit -m "<exact commit message from the stage block>"`.
   Never amend a committed stage. Never skip a stage commit. Never commit `.env`.

### 0.4 Branch Strategy
- Linear work on `main` (single developer). Tag milestones per §2.

### 0.5 Golden Rules
- Never commit before a stage's acceptance criteria pass.
- `.env` is git-ignored; only `.env.example` is committed.
- Shell is **Windows PowerShell 5.1**: no `&&`. Chain with `; if ($?) { ... }` or use separate calls.
- All backend work runs **inside Docker** (`python:3.12-slim`). Host has no Python 3.12 and
  Python 3.14 breaks torch/onnxruntime/docling wheels — do not build a host backend venv.
- One-off backend commands: `docker compose run --rm api <cmd>` (avoids PowerShell quoting pain).

---

## 1. Project Snapshot

| Item | Value |
| :--- | :--- |
| Project | Contexta Py — async multi-agent RAG platform |
| Repo root | `E:\Contexta` (git repo, branch `main`) |
| Backend | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 async |
| Agent | LangGraph (async graph, streaming) |
| Queue | Arq + Redis 7 |
| Parsing | `pymupdf4llm` (PyMuPDF) primary; Docling as optional heavy upgrade |
| Chunking | Hierarchical parent-child (2000-char parent / 400-char child) |
| Vector store | Qdrant — dense `BAAI/bge-base-en-v1.5` (768-dim) + sparse BM25, RRF fusion |
| Reranker | FlashRank (local ONNX) |
| LLM | Groq via `openai` SDK, `llama-3.3-70b-versatile` |
| Web search | Tavily |
| Object storage | MinIO (S3-compatible) via `aioboto3` |
| Frontend | Next.js 16 App Router, React 19, TS 5, Tailwind 4, shadcn/ui |
| PDF viewer | `@embedpdf/react-pdf-viewer` |
| TTS | `edge-tts` |
| Tests | pytest, pytest-asyncio, respx |

### 1.1 Local Toolchain (verified 2026-10-05)
| Tool | Installed | Note |
| :--- | :--- | :--- |
| Python | 3.14.6 (`C:\Python314`), 3.11 (WindowsApps) | **No 3.12 on host** → backend runs only in Docker on `python:3.12-slim`. |
| Node | v24.18.0 | Compatible with Next 16. |
| npm | 11.16.0 | Use `npm ci` once `package-lock.json` exists. |
| Docker | CLI 29.8.0, Compose v5.5.1 | **Daemon was NOT running** — Stage 1 starts Docker Desktop. |
| Git | present | Only `README.md` tracked, 2 commits. |

### 1.2 Ports (fixed for the project lifetime)
| Service | Host | Container |
| :--- | :--- | :--- |
| FastAPI | **8010** (see §13 — host 8000 was taken) | 8000 |
| Next.js | 3000 | 3000 |
| PostgreSQL | 5432 | 5432 |
| Redis | 6379 | 6379 |
| Qdrant REST / gRPC | 6333 / 6334 | 6333 / 6334 |
| Object storage API / console | 9000 / 9001 | 9000 / 9001 |

### 1.3 Core Data Model (from README, final)
- **Document**: `id UUID PK`, `title`, `file_url`, `file_key` (S3 object key), `size_bytes`,
  `status Enum(PENDING|PROCESSING|READY|FAILED)`, `project_id UUID`, `page_count int`,
  `error_message text|null`, `created_at`, `updated_at`.
- **DocumentChunk**: `id UUID PK`, `document_id FK`, `parent_chunk_id UUID|null`, `content text`,
  `summary text|null`, `page_number int`, `is_table bool`, `embedding_id str`, `char_start/char_end int|null`.
- **ChatMessage**: `id UUID PK`, `project_id UUID`, `role Enum(USER|ASSISTANT)`, `content text`,
  `citations JSONB`, `created_at`.

---

## 2. Milestone Map

| Milestone | Stages | Tag after stage |
| :--- | :--- | :--- |
| M1 Foundation | 1–3 | `milestone-01-foundation` |
| M2 Ingestion backend | 4–8 | `milestone-02-ingestion` |
| M3 Agent backend | 9–12 | `milestone-03-agents` |
| M4 Frontend | 13–17 | `milestone-04-frontend` |
| M5 Ship | 18–20 | `milestone-05-ship` |

---

## 3. Progress Tracker

Keep this table current — it is the fastest resume signal.

| Stage | Title | Commit message | Status |
| :--- | :--- | :--- | :--- |
| 1 | Repository & toolchain baseline | `chore: establish repo baseline with gitignore, env template and tooling config` | ✅ |
| 2 | Docker Compose infrastructure | `feat(infra): add compose stack for postgres, redis, qdrant and minio` | ✅ |
| 3 | Backend skeleton & data models | `feat(backend): bootstrap FastAPI app, config, database and SQLAlchemy models` | ✅ |
| 4 | Object storage & document CRUD | `feat(backend): add minio storage service and document upload/list/delete API` | ✅ |
| 5 | Ingestion worker & PDF parsing | `feat(worker): add arq worker with pdf parsing and parent-child chunking` | ⬜ |
| 6 | Embeddings & hybrid Qdrant index | `feat(worker): add batch embeddings and dense+sparse bm25 hybrid indexing` | ⬜ |
| 7 | Retrieval service (RRF) | `feat(services): add parallel dense and bm25 retrieval with rrf fusion` | ⬜ |
| 8 | FlashRank reranking | `feat(services): add flashrank onnx reranker with lazy loading` | ⬜ |
| 9 | LangGraph agent graph | `feat(agents): implement langgraph rag graph with router, multiquery, grader and fallback` | ⬜ |
| 10 | SSE chat streaming API | `feat(api): add sse chat stream endpoint with thought events and citations` | ⬜ |
| 11 | TTS endpoint | `feat(api): add edge-tts text to speech endpoint` | ⬜ |
| 12 | Backend tests & quality gates | `test(backend): add pytest suite with ruff and mypy gates` | ⬜ |
| 13 | Frontend scaffold | `chore(frontend): scaffold next.js 16 app with tailwind 4 and shadcn` | ⬜ |
| 14 | Frontend API + SSE clients | `feat(frontend): add typed api client and fetch-based sse parser` | ⬜ |
| 15 | Dashboard & document CRUD UI | `feat(frontend): add project dashboard with upload, status polling and delete` | ⬜ |
| 16 | Split PDF + chat workspace | `feat(frontend): add split pdf viewer and chat workspace with citation jump` | ⬜ |
| 17 | Chat streaming UX & TTS | `feat(frontend): stream agent thought timeline, tokens, citations and tts playback` | ⬜ |
| 18 | Full-stack integration | `feat: wire full stack in compose and verify end-to-end ingestion and chat` | ⬜ |
| 19 | Docs, scripts & polish | `docs: add developer runbook, scripts and architecture notes` | ⬜ |
| 20 | Final verification & release | `chore: final verification, seed script and v0.1.0 tag` | ⬜ |

---

## 4. Final Directory Structure (target)

```
E:\Contexta\
├── PLAN.md
├── README.md
├── AGENTS.md                      # agent runbook: commands, conventions, stage workflow
├── .env                           # git-ignored, real secrets
├── .env.example                   # committed template
├── .gitignore
├── docker-compose.yml             # infra + api + worker + frontend
├── Makefile                       # convenience targets (optional, PowerShell-safe)
├── scripts\
│   ├── dev-up.ps1, dev-down.ps1, dev-logs.ps1
│   ├── seed_demo_pdf.py           # generates a multi-page test PDF with a table
│   └── smoke_test.py              # end-to-end API smoke test
├── backend\
│   ├── Dockerfile                 # multi-stage: base -> api | worker
│   ├── pyproject.toml             # ruff/mypy/pytest config
│   ├── requirements.txt           # runtime
│   ├── requirements-dev.txt       # dev/test
│   ├── alembic.ini
│   ├── alembic\versions\...
│   ├── main.py                    # uvicorn entrypoint
│   ├── app\
│   │   ├── main.py                # FastAPI factory
│   │   ├── api\deps.py
│   │   ├── api\v1\router.py
│   │   ├── api\v1\chat.py
│   │   ├── api\v1\documents.py
│   │   ├── api\v1\tts.py
│   │   ├── api\v1\health.py
│   │   ├── core\config.py
│   │   ├── core\database.py
│   │   ├── core\logging.py
│   │   ├── core\errors.py
│   │   ├── core\events.py         # redis pub/sub bus for ingestion status
│   │   ├── models\base.py
│   │   ├── models\document.py
│   │   ├── models\chunk.py
│   │   ├── models\chat.py
│   │   ├── schemas\document.py, chat.py, common.py
│   │   ├── agents\state.py
│   │   ├── agents\graph.py
│   │   ├── agents\prompts.py
│   │   ├── agents\nodes\router.py, multiquery.py, retrieval.py, rerank.py, grader.py, generator.py, web_fallback.py
│   │   ├── services\storage.py    # S3/MinIO
│   │   ├── services\parser.py     # PyMuPDF -> markdown+pages
│   │   ├── services\chunker.py    # parent-child
│   │   ├── services\embedding.py  # fastembed batch
│   │   ├── services\hybrid_db.py  # qdrant dense+sparse
│   │   ├── services\reranker.py   # flashrank
│   │   ├── services\llm.py        # groq client + tokenizer
│   │   ├── services\tavily.py     # web search
│   │   ├── services\ingestion.py  # orchestrator used by worker
│   │   └── workers\tasks.py       # arq job entrypoints
│   └── tests\
│       ├── conftest.py
│       ├── test_health.py, test_documents.py, test_chunker.py, test_rrf.py,
│       ├── test_graph.py, test_sse.py, test_tts.py, test_storage.py
└── frontend\
    ├── Dockerfile
    ├── package.json, tsconfig.json, next.config.ts, components.json
    ├── postcss.config.mjs
    └── src\
        ├── app\layout.tsx, page.tsx, globals.css
        ├── app\dashboard\page.tsx
        ├── app\chat\[id]\page.tsx
        ├── components\ui\...          # shadcn
        ├── components\pdf-viewer\PdfPane.tsx, CitationLayer.tsx
        ├── components\chat\ChatPanel.tsx, ThoughtTimeline.tsx, TokenStream.tsx, CitationList.tsx, Composer.tsx
        ├── components\documents\UploadDropzone.tsx, DocumentTable.tsx, StatusBadge.tsx
        ├── lib\api.ts, sse.ts, types.ts, utils.ts
        └── hooks\useChat.ts, useDocuments.ts
```

---

---

# 5. Stage-by-Stage Steps

## STAGE 1 — Repository & Toolchain Baseline

**Goal:** deterministic, reproducible starting point: tooling running, ignore rules, env template, tooling config.

### Steps
- **S01.01** Start Docker Desktop and wait until the engine is up.
  `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"` then poll
  `docker info --format "{{.ServerVersion}}"` until it returns a version (first boot 1–3 min).
- **S01.02** ✔ CHECK toolchain: `docker --version; docker compose version; node --version; npm --version; py -0p`.
- **S01.03** Create the directory skeleton (empty dirs are not tracked by git — create files instead):
  `backend/app`, `backend/tests`, `backend/alembic/versions`, `scripts`, `frontend`.
- **S01.04** Write `.gitignore` (must cover): `.env`, `backend/.venv/`, `__pycache__/`, `*.py[cod]`,
  `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `frontend/node_modules/`, `frontend/.next/`,
  `frontend/out/`, `frontend/.env*.local`, `*.log`, `data/` (local minio volume), `uploads/`,
  `.DS_Store`, `Thumbs.db`, `*.sqlite3`, `qdrant_storage/`.
- **S01.05** Write `.env.example` — the authoritative list of every variable used in the project (see §6 for full list). Values must be placeholders/empty, never real keys.
- **S01.06** Write `AGENTS.md`: repo layout, stage-commit workflow, exact commands for run/test/lint, and the "never commit .env" rule. This is what future agent sessions read first.
- **S01.07** Write `backend/pyproject.toml` with tool config only (no build system): ruff (line-length 100, target py312, select E/F/I/UP/B/ASYNC/SIM), mypy (strict-ish, `ignore_missing_imports = true`), pytest (`asyncio_mode = auto`, `testpaths = ["tests"]`).
- **S01.08** Write `.editorconfig` (LF, UTF-8, 2-space for ts/tsx/json, 4-space for py) and `.gitattributes` (`* text=auto eol=lf`, `*.png binary`, `*.pdf binary`).
- **S01.09** Create branch-agnostic baseline commit: `git add -A; git commit -m "chore: establish repo baseline with gitignore, env template and tooling config"`.
- **S01.10** ✔ CHECK `git status --short` is clean; `git log --oneline -3` shows the commit.

### ✔ Acceptance Criteria
- `docker info` succeeds, Node/npm versions known.
- `.gitignore`, `.env.example`, `AGENTS.md`, `backend/pyproject.toml`, `.editorconfig` exist and are committed.
- `git status` clean.

⚠ RISK: Docker Desktop not installed at the default path → find it via
`Get-ChildItem "C:\Program Files\Docker" -Recurse -Filter "Docker Desktop.exe" -ErrorAction SilentlyContinue`;
if absent, install Docker Desktop (needs WSL2) or fall back to native installs
(Postgres/Redis/Qdrant/MinIO binaries) — record the deviation in §13.

---

## STAGE 2 — Docker Compose Infrastructure

**Goal:** all four stateful services running with healthchecks, persistent volumes, and a bucket auto-created.

### Files to create
- `docker-compose.yml` (infra-only first; app services added in Stage 18)
- `infra/minio/createbuckets.sh`
- `infra/qdrant/config.yaml` (optional)

### Steps
- **S02.01** Write `docker-compose.yml` with a shared `x-common-env` anchor so Postgres/Redis creds are defined once.
- **S02.02** `postgres:16-alpine`: env `POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB` from `.env`,
  volume `pgdata:/var/lib/postgresql/data`, healthcheck `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`, port 5432.
- **S02.03** `redis:7-alpine`: `command: ["redis-server","--appendonly","yes"]`, volume `redisdata:/data`,
  healthcheck `redis-cli ping`, port 6379.
- **S02.04** `qdrant/qdrant:v1.12.4`: volume `qdrantdata:/qdrant/storage`, ports `6333:6333`, `6334:6334`,
  env `QDRANT__SERVICE__API_KEY` optional, healthcheck `bash -c ':> /dev/tcp/127.0.0.1/6333'` (image has no curl).
- **S02.05** `minio/minio:latest` + `minio/mc:latest` (bootstrap sidecar): server command
  `server /data --console-address ":9001"`, healthcheck `mc ready local` style
  (`curl -f http://localhost:9000/minio/health/live` fallback), then a one-shot `createbuckets` service
  that runs until bucket `${MINIO_BUCKET:-contexta}` exists (`mc mb --ignore-existing`), mounting
  `infra/minio/createbuckets.sh`.
- **S02.06** Define named volumes `pgdata`, `redisdata`, `qdrantdata`, `miniodata`.
- **S02.07** Copy `.env.example` → `.env` and fill real values: `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`
  (generate with `python -c "import secrets;print(secrets.token_urlsafe(48))"`), plus placeholder API keys.
- **S02.08** ✔ CHECK `docker compose up -d postgres redis qdrant minio createbuckets` then
  `docker compose ps` — all four healthy; `curl http://localhost:6333/collections` returns `{"result":{"collections":[]}}`;
  `curl http://localhost:9001` reaches MinIO console; `docker compose logs createbuckets` shows bucket created.
- **S02.09** Commit: `feat(infra): add compose stack for postgres, redis, qdrant and minio`.

### ✔ Acceptance Criteria
All four services healthy, persistent volumes created, MinIO bucket exists, `docker compose ps` shows no restart loops.

⚠ RISK: port already in use on the host (common for 5432/6379) → find with
`Get-NetTCPConnection -LocalPort 5432 -State Listen` and change the *host* side of the mapping (container side and app URLs stay).

---

## STAGE 3 — Backend Skeleton, Config, Database & Models

**Goal:** runnable FastAPI app inside Docker with health endpoints, async SQLAlchemy wired, models + Alembic migration applied.

### Files to create
`backend/requirements.txt`, `backend/Dockerfile`, `backend/main.py`, `backend/app/main.py`,
`backend/app/core/config.py`, `database.py`, `logging.py`, `errors.py`, `api/deps.py`,
`api/v1/router.py`, `api/v1/health.py`, `models/base.py`, `models/document.py`, `models/chunk.py`,
`models/chat.py`, `schemas/common.py`, `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial.py`.

### Steps
- **S03.01** `backend/requirements.txt` — pin these (adjust patch versions only if resolution fails):
  `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `pydantic==2.10.4`, `pydantic-settings==2.7.0`,
  `sqlalchemy[asyncio]==2.0.36`, `asyncpg==0.30.0`, `alembic==1.14.0`, `greenlet==3.1.1`,
  `arq==0.26.3`, `redis==5.2.1`, `httpx==0.28.1`, `python-multipart==0.0.20`,
  `aioboto3==13.2.0`, `pymupdf4llm==0.0.17`, `pymupdf==1.25.1`,
  `fastembed==0.5.1`, `qdrant-client==1.12.2`, `flashrank==0.2.10`, `openai==1.59.6`,
  `langgraph==0.2.60`, `langchain-core==0.3.28`, `edge-tts==7.0.0`,
  `tenacity==9.0.0`, `orjson==3.10.13`, `structlog==24.4.0`, `python-dotenv==1.0.1`.
  ⚠ RISK: `pymupdf4llm` pulls a pinned `pymupdf` — if versions conflict, install `pymupdf4llm` without pin and let it resolve; record in §13.
- **S03.02** `backend/requirements-dev.txt`: `-r requirements.txt`, `pytest==8.3.4`, `pytest-asyncio==0.25.0`,
  `pytest-cov==6.0.0`, `respx==0.22.0`, `ruff==0.8.6`, `mypy==1.14.1`, `types-aioboto3`, `aiosqlite` (for in-memory tests).
- **S03.03** `backend/Dockerfile` — multi-stage:
  - stage `base`: `FROM python:3.12-slim`; env `PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1`;
    install `libpq5`? (not needed with asyncpg) but **do** install `curl` (healthcheck) and `build-essential` + `libglib2.0-0 libgl1` (PyMuPDF render deps).
  - stage `api`: copy `requirements*.txt`, install, copy `app/`, `main.py`, `alembic*`; `EXPOSE 8000`;
    `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`.
  - stage `worker`: same base + copy worker entrypoint; `CMD ["arq","app.workers.tasks.WorkerSettings"]`.
  - `HEALTHCHECK CMD curl -f http://localhost:8000/api/v1/health || exit 1`.
- **S03.04** `backend/app/core/config.py`: `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)`;
  fields per §6; `@lru_cache def get_settings() -> Settings`.
  ⛔ DECISION: prefix env vars with `CONTEXTA_`? → **No prefix** (README-era simplicity), but keep `model_config` case-insensitive.
- **S03.05** `backend/app/core/database.py`: `create_async_engine(pool_pre_ping=True, pool_size=10, max_overflow=20)`,
  `async_sessionmaker(expire_on_commit=False)`, `Base = declarative_base()`, `get_session()` dependency, plus
  `get_redis()` returning a module-level `redis.asyncio.Redis.from_url(..., decode_responses=True)` singleton.
- **S03.06** Models — `Document`, `DocumentChunk`, `ChatMessage` exactly per §1.3, with
  `UUID(as_uuid=True)` + `sqlalchemy.dialects.postgresql.JSONB` for citations, indexes on
  `(project_id, created_at)`, `(document_id, page_number)`, `Enum(..., native_enum=False)` so Alembic works everywhere.
- **S03.07** Alembic: `alembic.ini` (`script_location = alembic`, `sqlalchemy.url` left empty), async `env.py`
  using `Base.metadata` autogenerate target, `0001_initial.py` creating the 3 tables + indexes.
- **S03.08** `backend/app/main.py`: `create_app()` with CORS allow-list from `settings.cors_origins`,
  `lifespan` that (a) verifies DB connectivity, (b) ensures the Qdrant collection exists, (c) ensures the MinIO bucket exists,
  router mount at `/api/v1`, global exception handlers returning the §9 error envelope.
- **S03.09** `backend/app/api/v1/health.py`: `GET /health` (liveness, always 200 once app is up) and
  `GET /health/ready` (pings Postgres, Redis, Qdrant, MinIO; 503 if any is down; returns per-dependency latency).
- **S03.10** `backend/app/core/logging.py`: `structlog` JSON logger + stdlib fallback, request-id middleware in `app/main.py`.
- **S03.11** Add api/worker services to `docker-compose.yml` (profiles `app` so infra can come up alone for now):
  `build: {context: ./backend, target: api}`, `env_file: .env`, `depends_on: {postgres: {condition: service_healthy}, ...}`,
  `ports: ["8000:8000"]`, `volumes: ["./backend/app:/app/app"]` for hot reload in dev, restart `unless-stopped`.
- **S03.12** ✔ CHECK `docker compose --profile app up -d --build api`; then
  `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}`;
  `curl http://localhost:8000/api/v1/health/ready` → all four `ok`;
  `docker compose run --rm api alembic upgrade head` → 3 tables created;
  `docker compose exec postgres psql -U contexta -d contexta -c "\dt"` lists `documents`, `document_chunks`, `chat_messages`.
- **S03.13** Commit: `feat(backend): bootstrap FastAPI app, config, database and SQLAlchemy models`.

### ✔ Acceptance Criteria
- `/health` 200, `/health/ready` 200 with all deps ok.
- Alembic upgrade head succeeds and is idempotent on re-run.
- Container logs show no tracebacks; `/docs` renders.

⚠ RISK: build takes 3–6 min on first run (PyMuPDF + fastembed wheels are large). Use `--progress=plain` if quiet output hides errors.

---

## STAGE 4 — Object Storage & Document CRUD API

**Goal:** upload a PDF → instant ack (<200 ms) with `job_id`, status lifecycle endpoints, delete, and presigned URL.

### Files to create
`app/services/storage.py`, `app/schemas/document.py`, `app/api/v1/documents.py`, `app/core/events.py`,
`app/workers/__init__.py` (stub `tasks.py` so ArqSettings import works later).

### Steps
- **S04.01** `storage.py`: `StorageClient` class wrapping `aioboto3` with
  `ensure_bucket()`, `upload(fileobj|bytes, key, content_type)`, `download(key) -> bytes`,
  `presigned_get(key, expires=3600)`, `delete(key)`, `exists(key)`.
  Configure with `endpoint_url=settings.minio_endpoint`, `aws_access_key_id`, `aws_secret_access_key`,
  `region_name="us-east-1"`, `use_ssl=False`; instantiate once in `lifespan` and cache on `app.state.storage`.
- **S04.02** `app/core/events.py`: Redis pub/sub wrapper `publish(channel, payload: dict)` and
  `async def event_stream(request)` generator used by the SSE status endpoint. Channel name: `documents:{project_id}`.
- **S04.03** `schemas/document.py`: Pydantic v2 models `DocumentOut`, `DocumentListOut`, `UploadAccepted(job_id, document_id, status)`.
- **S04.04** `app/api/v1/documents.py`:
  - `POST /api/v1/documents` (multipart: `file`, `project_id`, optional `title`) → validate content-type/extension (`.pdf` only),
    stream to MinIO under `documents/{project_id}/{uuid}.pdf`, insert `Document(status=PENDING)`, commit, return `202` with `job_id`.
    ⛔ DECISION: `project_id` is a client-supplied UUID with no auth in v0.1 (documented in §13 as intentional simplification).
  - `GET /api/v1/documents?project_id=` → list, newest first.
  - `GET /api/v1/documents/{id}` → detail + chunk count.
  - `DELETE /api/v1/documents/{id}` → delete S3 object + cascade chunks + delete Qdrant points by filter.
  - `GET /api/v1/documents/{id}/file` → 302 redirect to presigned URL (keeps MinIO private).
  - `GET /api/v1/documents/events` → SSE stream of status changes (used by the dashboard).
- **S04.05** ⛔ DECISION: dispatch to the worker now or in Stage 5? → **Now**, but behind a feature flag
  `settings.worker_dispatch_enabled` so the endpoint works standalone; wire `arq` `create_pool` + `enqueue_job("ingest_document", ...)` in Stage 5.
- **S04.06** ✔ CHECK with a real PDF: `curl -F "file=@scripts/seed_demo_pdf.py" ...` — first create a test PDF:
  `pip`-free approach: use `pymupdf` inside the api container: `docker compose run --rm api python -c "import fitz; d=fitz.open(); p=d.new_page(); p.insert_text((72,100),'Contexta Py demo'); d.save('/tmp/t.pdf')"`,
  copy out, then `curl -F "file=@/tmp/t.pdf" -F "project_id=<uuid>" http://localhost:8000/api/v1/documents`
  → `202 {"job_id": ..., "status": "PENDING"}` in <1 s; `GET /api/v1/documents/{id}` shows the row;
  MinIO console shows the object at `http://localhost:9001`.
- **S04.07** Commit: `feat(backend): add minio storage service and document upload/list/delete API`.

### ✔ Acceptance Criteria
Upload returns 202 fast, row + object exist, list/detail/delete work, presigned URL opens the PDF, OpenAPI shows all routes.

⚠ RISK: large-file upload buffering — always stream to MinIO via `upload_fileobj`; never read the whole body into RAM.

---

## STAGE 5 — Ingestion Worker & PDF Parsing

**Goal:** Arq worker that downloads the PDF, extracts layout-aware Markdown with page mapping, and produces parent-child chunks — fully unit-testable without embeddings.

### Files to create
`backend/app/services/parser.py`, `chunker.py`, `ingestion.py`, `backend/app/workers/tasks.py`.

### Steps
- **S05.01** `parser.py` contract:
  ```python
  @dataclass
  class ParsedPage: page_number: int; markdown: str; tables: list[str]
  @dataclass
  class ParsedDocument: pages: list[ParsedPage]; full_markdown: str; page_count: int
  async def parse_pdf(data: bytes, *, docling: bool = False) -> ParsedDocument
  ```
- **S05.02** Implement with `pymupdf4llm.to_markdown(doc, page_chunks=True)` which returns a list of `{text, metadata.page}`.
  Normalize: strip repeated headers/footers (a line appearing on >60% of pages), collapse 3+ blank lines, keep page boundaries.
- **S05.03** Extract tables per page: `page.find_tables()` from PyMuPDF → `.to_markdown()`; store into `ParsedPage.tables`.
  ⛔ DECISION: Docling now or later? → **Later/opt-in.** Docling pulls torch (~2 GB). Ship PyMuPDF first, add
  `CONTEXTA_PARSER=docling` + a second Dockerfile target in Stage 19 if layout quality demands it.
- **S05.04** `chunker.py`:
  - `split_tables(tables) -> list[ChunkDraft(is_table=True, summary_placeholder=...)]`
  - `parent_child_split(text, parent_size=2000, child_size=400, overlap=60) -> list[ChunkDraft]`
    using sentence-aware regex split (`(?<=[.!?])\s+`), then sliding window; every child stores `parent_index`.
  - `ChunkDraft` fields: `content`, `parent_content`, `page_number`, `is_table`, `char_start`, `char_end`.
- **S05.05** `ingestion.py`: `async def ingest_document(document_id: UUID) -> IngestionResult` orchestrator with phases,
  updating `Document.status` and `error_message` at each boundary and publishing an SSE event after each phase:
  `FETCHING → PARSING → CHUNKING → SUMMARIZING → EMBEDDING → INDEXING → READY | FAILED`.
  - Wrap every phase in `tenacity.retry` (3 attempts, exponential backoff) except parsing of corrupt files.
  - Emit progress as `percent` 0→100 so the UI can show a real progress bar.
- **S05.06** Table summarization: for each `is_table` chunk, call the LLM once with a 60-token summary prompt;
  run at most 5 concurrently via `asyncio.gather` + `Semaphore(5)`; on LLM failure store `summary=None` and continue (never fail ingestion for a summary).
- **S05.07** `workers/tasks.py`: `async def ingest_document(ctx, document_id: str)` wrapper + `class WorkerSettings(arq.connections.RedisSettings)`
  with `functions=[ingest_document]`, `max_jobs=2`, `job_timeout=1800`, `keep_result=3600`,
  `retry_jobs=True`, `on_startup=bootstrap` (open DB session factory, ensure bucket/collection).
  Also define `class WorkerSettingsLight` used by the API image (no parser/embedding imports) so the API stays slim.
- **S05.08** Wire dispatch in `documents.py` (behind the Stage 4 flag): `await arq_pool.enqueue_job("ingest_document", str(document_id))`.
- **S05.09** ✔ CHECK `docker compose --profile app up -d --build`; `docker compose logs -f worker`;
  re-upload a multi-page PDF; watch log lines `phase=PARSING ... phase=CHUNKING`; then
  `curl http://localhost:8000/api/v1/documents/<id>` → `page_count` correct; `SELECT count(*) FROM document_chunks` > 0; status `READY` (or `PROCESSING` if Stage 6 not done — acceptable, note it).
- **S05.10** Commit: `feat(worker): add arq worker with pdf parsing and parent-child chunking`.

### ✔ Acceptance Criteria
Ingestion completes without touching the request thread, chunk rows persisted with page numbers, table chunks flagged, failures recorded in `error_message` (upload a text file renamed `.pdf` to verify the FAILED path).

⚠ RISK: `pymupdf4llm` API drift — confirm the returned key is `text`/`metadata` in the installed version; if it is `pages`, adapt in `parser.py` only.

---

## STAGE 6 — Embeddings & Hybrid Qdrant Index

**Goal:** batch dense embeddings (fastembed/bge-base-en-v1.5, 768-dim) + sparse BM25 vectors into one Qdrant collection, parent text stored in payload.

### Files to create
`backend/app/services/embedding.py`, `backend/app/services/hybrid_db.py`.

### Steps
- **S06.01** `embedding.py`: singleton `EmbeddingService` with `fastembed.TextEmbedding("BAAI/bge-base-en-v1.5")`,
  `async def embed_documents(texts: list[str], batch=32) -> list[list[float]]` running the sync
  `model.embed(texts, batch_size=batch)` inside `asyncio.to_thread` + `Semaphore(2)` to bound CPU/memory.
  Also `embed_query(text)` (bge wants the query instruction prefix `"query: "` for retrieval asymmetry — use it for queries only).
  Model download happens on first call (~440 MB) → cache dir `settings.model_cache_dir` mounted as a volume.
- **S06.02** `hybrid_db.py`:
  - `ensure_collection()` creates `contexta_chunks` with vectors named `dense` (size 768, COSINE) and `bm25` (sparse),
    payload schema indexes on `document_id`, `project_id`, `page_number` (keyword) and a text index on `content`.
  - `upsert_chunks(points)` where payload = `{document_id, project_id, page_number, content, summary, is_table,
    parent_id, parent_content, title, chunk_index}` and names = `f"{document_id}:{chunk_index}"` (deterministic → idempotent re-ingest).
  - Sparse vectors: use Qdrant's recommended sparse encoder
    `fastembed.SparseTextEmbedding(model_name="Qdrant/bm25")`; if the model cannot be fetched, fall back to a hand-rolled
    hashing sparse vector (documented in §13) so the pipeline never hard-fails.
  - `delete_document(document_id)` via `models.Filter` on `document_id`.
  - `hybrid_search(dense_vec, sparse_vec, top_k=20)` using `client.query_points` with `Prefetch` ×2 + `Fusion(fusion=FusionType.RRF)`.
- **S06.03** Hook into `ingestion.py`: after chunking → embed children in batches → build points → upsert in pages of 256 → then set `Document.status = READY` and publish the `READY` event.
- **S06.04** Idempotency: before upserting, `delete_document(document_id)` so a re-run of a FAILED document does not duplicate points.
- **S06.05** ✔ CHECK `curl http://localhost:6333/collections/contexta_chunks` → 2 named vectors;
  `docker compose run --rm api python -c "..."` (script in `scripts/verify_index.py`) inserts 2 dummy points and runs a RRF query returning them;
  `SELECT count(*) FROM document_chunks` equals `points_count` reported by Qdrant.
- **S06.06** Commit: `feat(worker): add batch embeddings and dense+sparse bm25 hybrid indexing`.

### ✔ Acceptance Criteria
Both vector spaces populated, re-running ingestion does not duplicate points, `READY` status + SSE event fire on completion, first-call model download is cached in a volume.

⚠ RISK: fastembed model download needs internet inside the container; if the environment is offline, set
`CONTEXTA_EMBEDDING_BACKEND=hash` (deterministic 768-dim hashing fallback) so stages 7+ still run — record in §13.

---

## STAGE 7 — Retrieval Service (parallel dense + BM25 with RRF)

**Goal:** one callable, fully concurrent hybrid retriever used by the agent graph and testable in isolation.

### Files to create
`backend/app/services/retrieval.py`, `backend/tests/test_rrf.py`.

### Steps
- **S07.01** `retrieval.py` contract:
  ```python
  @dataclass
  class RetrievedChunk:
      chunk_id: str; document_id: str; title: str; page_number: int
      content: str; summary: str | None; score: float; dense_score: float | None; sparse_score: float | None
  async def retrieve(query: str, project_id: UUID, top_k: int = 8, *, candidates: int = 20) -> list[RetrievedChunk]
  ```
- **S07.02** Concurrency: in one coroutine, `await asyncio.gather(embed_query(query), sparse_encode(query))`
  → `await hybrid_db.hybrid_search(...)`. Expose `timings` for the SSE `retrieval` event (`dense_ms`, `sparse_ms`, `fusion_ms`).
- **S07.03** Post-process: drop chunks whose document status is not `READY` (one batched Postgres query, cached 30 s in-process), truncate `content` to `settings.retrieval_max_chars` (default 1500) with an ellipsis, keep `parent_content` available but not embedded in the prompt unless needed.
- **S07.04** Pure helper `rrf_fuse(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]` implemented in-repo too — it is the documented algorithm and gives a deterministic unit test independent of Qdrant.
- **S07.05** `backend/tests/test_rrf.py`: asserts `rrf_fuse` ordering, that one query with no results returns `[]`, and that project filtering excludes foreign chunks.
- **S07.06** ✔ CHECK `docker compose run --rm api pytest tests/test_rrf.py -q` → green;
  manual: ingest a PDF containing the sentence *"The refund window is 30 days."* and run
  `docker compose run --rm api python scripts/query_probe.py "how long do I have to refund?"` → prints ranked chunks with page numbers.
- **S07.07** Commit: `feat(services): add parallel dense and bm25 retrieval with rrf fusion`.

### ✔ Acceptance Criteria
Single `await retrieve(...)` call returns merged, filtered, typed chunks in <400 ms for a 500-chunk collection; unit tests pass; probe script finds the planted sentence.

---

## STAGE 8 — FlashRank Reranking

**Goal:** local ONNX cross-encoder rerank of candidates to top-K, lazy-loaded, no network at query time.

### Files to create
`backend/app/services/reranker.py`, `backend/tests/test_reranker.py`.

### Steps
- **S08.01** `RerankerService` singleton with `from_pretrained("ms-marco-MiniLM-L-12-v2", cache_dir=...)`,
  loaded in a `threading.Lock`-guarded lazy `ensure_loaded()`; expose `model_ready()` for `/health/ready`.
- **S08.02** `async def rerank(query, chunks, top_k=5, *, min_score=0.0) -> list[RetrievedChunk]`:
  `passages = [{"id": c.chunk_id, "text": c.content, "meta": {}}]`; `await asyncio.to_thread(self._rank, query, passages)`;
  map scores back to `RetrievedChunk`, drop `< min_score`, sort desc.
- **S08.03** `top_k`/`min_score` come from settings (`rerank_top_k=5`, `rerank_min_score=0.0`); the grader threshold in Stage 9 is separate and defaults to 70 on the *grader's* 0–100 scale.
- **S08.04** Graceful degradation: wrap `_rank` in try/except; on failure log a warning and return the input order truncated to `top_k` (never fail the query).
- **S08.05** ✔ CHECK `docker compose run --rm api pytest tests/test_reranker.py -q` (mocked);
  real run: first call downloads ~90 MB ONNX (cached in the volume), then `rerank_probe.py` shows scores in [0,1] and reordered output; measure latency and record it in §12.
- **S08.06** Commit: `feat(services): add flashrank onnx reranker with lazy loading`.

### ✔ Acceptance Criteria
Rerank returns ≤5 chunks in input→output mapped order; survives a missing model; warm latency <50 ms for 20 candidates.

⚠ RISK: `flashrank` wheels for Windows are irrelevant here (Linux container); if install fails on `python:3.12-slim`, add `onnxruntime==1.19.2` explicitly.

---

## STAGE 9 — LangGraph Agent Graph

**Goal:** the full async graph from the README — router → parallel multiquery → hybrid retrieval → rerank → async grader → generator **or** Tavily web fallback.

### Files to create
`app/agents/state.py`, `prompts.py`, `graph.py`, `nodes/router.py`, `multiquery.py`, `retrieval.py`, `rerank.py`, `grader.py`, `generator.py`, `web_fallback.py`, `app/services/llm.py`, `app/services/tavily.py`, `tests/test_graph.py`.

### Steps
- **S09.01** `services/llm.py`: `LLMClient` around the `openai` SDK (`AsyncOpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")`),
  exposing `chat(messages, *, temperature, max_tokens, model)` and `astream_chat(...)`; retries via tenacity; a `MockLLM` used when `settings.llm_backend=mock` (deterministic, for tests/CI).
- **S09.02** `state.py`: `class GraphState(TypedDict, total=False)` with
  `query, project_id, intent, queries, chunks, reranked, graded_chunks, answer, citations, web_results,
  trace, error, session_id, model`.
- **S09.03** `nodes/router.py`: one LLM call returning JSON `{intent: "document"|"general"|"personal", rewritten_query: str}`;
  robust parse (strip code fences, fall back to keyword heuristic).
- **S09.04** `nodes/multiquery.py`: `await asyncio.gather(*[rewrite(q) for q in prompts3])` producing 3 query variants;
  include the original query as a 4th when `settings.multiquery_count=3`.
- **S09.05** `nodes/retrieval.py`: `asyncio.gather(*[retrieve(q, project_id) for q in queries])` → merge with `rrf_fuse` → cap at `settings.retrieval_candidates` (default 40).
- **S09.06** `nodes/rerank.py`: delegate to Stage 8.
- **S09.07** `nodes/grader.py`: grade all candidates concurrently with `asyncio.gather` + `Semaphore(8)`; each call returns
  `{relevant: bool, score: 0-100, reason: str}`; keep chunks with `score >= settings.grader_threshold` (default 70);
  emit `graded_count` / `avg_score` into the trace.
- **S09.08** `nodes/web_fallback.py`: `services/tavily.py` calls Tavily `POST /search` via `httpx` (injectable client for respx tests);
  returns normalized `{title, url, content}` results; on missing API key, emit a trace step and return an empty list.
- **S09.09** `nodes/generator.py`: build the prompt with numbered sources `[1] title p.12`; stream tokens via `llm.astream_chat`;
  accumulate into `answer` and `citations` (`document_id`, `page_number`, `title`, `chunk_id`, `snippet`).
- **S09.10** `graph.py`: `StateGraph(GraphState)`; nodes `router, multiquery, retrieval, rerank, grader, generator, web_fallback`;
  edges `START→router`; conditional edges from `grader`: `graded_chunks` non-empty → `generator`, else → `web_fallback` → `generator`;
  `generator → END`. `compile()` once in a module-level lazy accessor `get_graph()`.
- **S09.11** Trace emission: every node appends `{"step": ..., "message": ...}` to `state["trace"]` so the SSE layer can forward it verbatim (matches the README event vocabulary: `routing, expanding, retrieval, reranking, grading, generating, web_fallback, done`).
- **S09.12** ✔ CHECK `docker compose run --rm api pytest tests/test_graph.py -q` with `LLM_BACKEND=mock`:
  - (a) intent `general` answers without retrieval,
  - (b) intent `document` + good chunks → generator,
  - (c) all chunks graded < 70 → web_fallback invoked (assert with a respx-mocked Tavily).
- **S09.13** Commit: `feat(agents): implement langgraph rag graph with router, multiquery, grader and fallback`.

### ✔ Acceptance Criteria
Graph compiles once, all three routing outcomes verified by tests, trace vocabulary matches README, no blocking I/O in nodes.

⚠ RISK: `langgraph` API differs across minors (`StateGraph` import path, `astream_events`). Pin `langgraph==0.2.60` and verify with `pip show langgraph` inside the container; if `astream` semantics differ, fall back to `graph.ainvoke` + manual token loop in the SSE layer (documented fallback).

---

## STAGE 10 — SSE Chat Streaming API

**Goal:** `POST /api/v1/chat/stream` emitting the README's thought stream, persisting the turn to `chat_messages`, and exposing history.

### Files to create
`app/schemas/chat.py`, `app/api/v1/chat.py`, `app/services/chat_service.py`, `tests/test_sse.py`.

### Steps
- **S10.01** SSE response shape (exact, matches README):
  `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`;
  frames `data: {json}\n\n`; terminal frame `data: {"event":"done", ...}` then close. Heartbeat comment `: ping\n\n` every 15 s.
- **S10.02** Event vocabulary (JSON keys): `agent_state {step, message}`, `citations {items:[...]}`, `token {content}`,
  `error {message}`, `done {session_id, message_id}`.
- **S10.03** `chat_service.py`: `stream_chat(query, project_id, session_id) -> AsyncIterator[dict]` wrapping
  `graph.astream(..., stream_mode=["updates"])`; translate node updates into `agent_state` events; forward generator deltas as `token`;
  persist the assistant message (content + citations) with `ChatMessage`, and the user message, in one transaction at the end.
- **S10.04** `app/api/v1/chat.py`:
  - `POST /api/v1/chat/stream` (body: `query`, `project_id`, `session_id`) → SSE.
  - `GET /api/v1/chat/history/{session_id}` → messages with citations.
  - `DELETE /api/v1/chat/history/{session_id}` → clear.
- **S10.05** Client-disconnect handling: wrap the generator in try/except `(asyncio.CancelledError, ClientDisconnect)`; persist partial answer, publish a `done` frame with `partial: true` when possible.
- **S10.06** Guardrails: max query length 2000 chars; rate-limit per session (simple Redis token bucket, 20 req/min) — keep it minimal but present.
- **S10.07** ✔ CHECK `curl -N -X POST http://localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"query":"...","project_id":"<uuid>","session_id":"s1"}'`
  prints `agent_state routing` → `expanding` → `retrieval` → `reranking` → `grading` → `generating` → `token ...` → `citations` → `done`, in order, with no buffering (each line appears immediately).
  Then `GET /api/v1/chat/history/s1` returns both messages.
- **S10.08** ✔ CHECK `docker compose run --rm api pytest tests/test_sse.py -q` — asserts event ordering, the `text/event-stream` header, and that `done` is last.
- **S10.09** Commit: `feat(api): add sse chat stream endpoint with thought events and citations`.

### ✔ Acceptance Criteria
No buffering through the whole stack, ordered events, persisted history, disconnect-safe.

---

## STAGE 11 — Text-to-Speech Endpoint

**Goal:** `edge-tts` audio streaming so the frontend can read answers aloud.

### Files to create
`app/api/v1/tts.py`, `tests/test_tts.py`.

### Steps
- **S11.01** `POST /api/v1/tts` body `{text, voice?="en-US-AriaNeural", rate?, volume?}`; validate `len(text) <= 5000` and voice against `settings.tts_allowed_voices` prefix list.
- **S11.02** Implementation: `edge_tts.Communicate(text, voice, rate=rate).stream()` → iterate `audio` chunks → return
  `StreamingResponse(audio_bytes(), media_type="audio/mpeg")`. Set `Content-Disposition: inline; filename="speech.mp3"`.
- **S11.03** Add `GET /api/v1/tts/voices` returning a small curated list (e.g. `en-US-AriaNeural`, `en-US-GuyNeural`, `en-GB-SoniaNeural`) so the UI has a stable subset.
- **S11.04** ⚠ Guard: edge-tts requires internet to Microsoft. Add `settings.tts_enabled` and return `503 {"error":{"code":"tts_unavailable"}}` when disabled, so the frontend can hide the button.
- **S11.05** ✔ CHECK `curl -X POST http://localhost:8000/api/v1/tts -H "Content-Type: application/json" -d '{"text":"hello from contexta"}' -o speech.mp3` → file > 10 KB and plays; with `TTS_ENABLED=false` → 503.
- **S11.06** Commit: `feat(api): add edge-tts text to speech endpoint`.

### ✔ Acceptance Criteria
Valid mp3 returned, 503 when disabled, voices endpoint populated.

---

## STAGE 12 — Backend Tests, Lint & Type Gates

**Goal:** CI-grade checks so later stages cannot regress the backend.

### Steps
- **S12.01** `backend/tests/conftest.py`: fixtures `anyio_backend`, `settings_test` (SQLite `aiosqlite` URL, `LLM_BACKEND=mock`),
  `client` (`httpx.AsyncClient` + `ASGITransport`), `db_session` (create/drop schema), `fake_qdrant` (in-memory stub of `hybrid_db`),
  `fake_storage` (tmp dir stub), plus `pytest_asyncio` auto mode.
- **S12.02** Unit tests: `test_chunker.py` (parent/child sizes, overlap, table flag), `test_parser.py` (fixture PDF → pages + table markdown),
  `test_reranker.py`, `test_rrf.py` (from Stage 7), `test_graph.py` (from Stage 9), `test_storage.py`, `test_sse.py`, `test_tts.py`, `test_health.py`.
- **S12.03** Integration test `tests/test_documents_api.py` (upload → PENDING; patched dispatch → PROCESSING/READY), `tests/test_chat_api.py`.
- **S12.04** Create fixture PDFs programmatically in `tests/conftest.py` (`fitz`) so no binary files are committed.
- **S12.05** Add `backend/docker-compose.test.yml`? ⛔ DECISION → **No**; instead document `docker compose run --rm api pytest` as the canonical test command.
- **S12.06** Quality gates (all must pass): `ruff check .`, `ruff format --check .`, `mypy app`, `pytest -q --cov=app --cov-report=term-missing` (target ≥70% on `app/services` and `app/agents`).
- **S12.07** ✔ CHECK run all four commands inside the container; paste output into §3 notes.
- **S12.08** Commit: `test(backend): add pytest suite with ruff and mypy gates`.

### ✔ Acceptance Criteria
`pytest` green, `ruff` clean, `mypy` has no unignored errors, coverage reported.

⚠ RISK: mypy strict on LangGraph/`flashrank` untyped deps → keep `ignore_missing_imports = true` and add narrow `# type: ignore` only where unavoidable, recorded in §13.

---

## STAGE 13 — Frontend Scaffold (Next.js 16)

**Goal:** typed, lint-clean Next.js app with Tailwind 4 + shadcn/ui, wired to the API in dev.

### Steps
- **S13.01** Scaffold **inside the existing folder** (do not let create-next-app create `frontend/frontend`):
  `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --turbopack --yes`
  ⚠ RISK: newest Next may be >16; if `next@latest` is 15, pin `create-next-app@16` — verify with `npm ls next` inside `frontend`.
- **S13.02** Confirm `frontend/package.json` has `next@16`, `react@19`, `tailwindcss@4`, `@tailwindcss/postcss`.
- **S13.03** `npm i @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react`
  and shadcn init: `npx shadcn@latest init -d -y` then add
  `button card input label textarea badge dialog dropdown-menu select skeleton scroll-area separator tabs tooltip avatar sonner`.
- **S13.04** `src/lib/utils.ts` with `cn()`; `src/lib/types.ts` mirroring backend schemas (`Document`, `DocumentStatus`, `Chunk`, `Citation`, `SseEvent`).
- **S13.05** Env: `frontend/.env.local` (git-ignored) with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` and
  `NEXT_PUBLIC_PROJECT_ID=<stable uuid>`; also add `.env.example` in `frontend/` with the same keys and a note that these are public.
- **S13.06** Root layout: dark-capable theme, `<Toaster />` from sonner, font from `next/font` (Inter), `metadata.title = "Contexta Py"`.
- **S13.07** `src/app/page.tsx`: minimal landing with links to `/dashboard` and `/chat/demo` and a health-check button that pings `${NEXT_PUBLIC_API_URL}/health`.
- **S13.08** ✔ CHECK `npm run lint`, `npm run build`, and `npm run dev` (background) → `curl http://localhost:3000` 200 and no build errors.
- **S13.09** Commit: `chore(frontend): scaffold next.js 16 app with tailwind 4 and shadcn`.

### ✔ Acceptance Criteria
`npm run build` clean, shadcn components importable, landing page renders.

---

## STAGE 14 — Frontend API Client & Fetch-based SSE Parser

**Goal:** one typed HTTP client plus a reusable SSE reader (POST-based, since `EventSource` can't POST).

### Files to create
`src/lib/api.ts`, `src/lib/sse.ts`.

### Steps
- **S14.01** `api.ts`: `const API = process.env.NEXT_PUBLIC_API_URL`; `request<T>(path, init)` with JSON handling, `ApiError {code, message, status}` parsing from the backend envelope, and typed methods:
  `listDocuments`, `getDocument`, `uploadDocument(file, projectId, onProgress)` (uses `XMLHttpRequest` for real upload progress — `fetch` has no upload progress),
  `deleteDocument`, `getFileUrl(id)`, `chatHistory(sessionId)`, `clearHistory(sessionId)`, `ttsUrl(text, voice)`.
- **S14.02** `sse.ts`: `export async function* streamPostSSE(url, body, signal): AsyncGenerator<SseEvent>` —
  `fetch(url, {method:'POST', body: JSON.stringify(body), signal})` → read `res.body.getReader()`,
  decode with `TextDecoder({stream:true})`, split on `\n\n`, parse `data:` lines, `JSON.parse`, `yield` typed events; on `event:"done"` return.
  Handle `[DONE]`-style sentinels, ignore `:` comment heartbeats, and throw on non-2xx after reading the error body.
- **S14.03** ✔ CHECK `npx tsc --noEmit` clean; temporary dev route `/api/_sse_probe` that consumes the stream and logs events → confirms parsing against the live backend.
- **S14.04** Commit: `feat(frontend): add typed api client and fetch-based sse parser`.

### ✔ Acceptance Criteria
Typed methods match backend routes exactly; SSE parser yields events in order; `tsc` clean.

---

## STAGE 15 — Dashboard & Document CRUD UI

**Goal:** the "Instant Upload Ack" experience: dropzone, instant row with `PROCESSING`, live status, page count, open/delete.

### Files to create
`src/app/dashboard/page.tsx`, `src/hooks/useDocuments.ts`, `src/components/documents/UploadDropzone.tsx`, `DocumentTable.tsx`, `StatusBadge.tsx`.

### Steps
- **S15.01** `useDocuments.ts`: `useState` list + `refresh()`; optimistic insert on upload response; subscribe to
  `GET /documents/events` **via `streamPostSSE`** with a fallback 3-second polling loop when the SSE endpoint is unavailable;
  `useEffect` cleanup aborts the stream; statuses drive a `StatusBadge` (PENDING grey, PROCESSING amber + spinner, READY emerald, FAILED red + tooltip with `error_message`).
- **S15.02** `UploadDropzone.tsx`: drag-and-drop + click, accepts `.pdf`, shows per-file progress bar from `onProgress`, disables during upload, multiple files sequentially.
- **S15.03** `DocumentTable.tsx`: title (link to `/chat/{id}`), status, pages, chunk count, size, created-at, actions (Open / Copy link / Delete with `Dialog` confirm).
- **S15.04** Empty state, error toast via sonner, and a "Retry failed" action that re-triggers ingest for a FAILED document (`POST /documents/{id}/retry` — if not implemented, add it in Stage 19).
- **S15.05** ✔ CHECK manual: upload 3 PDFs (one small, one 60-page, one corrupt) → instant ack, statuses progress PROCESSING → READY, corrupt one shows FAILED with a message; delete removes row + object.
- **S15.06** Commit: `feat(frontend): add project dashboard with upload, status polling and delete`.

### ✔ Acceptance Criteria
Upload feels instant, statuses update without manual refresh, delete works, no console errors, `npm run build` passes.

---

## STAGE 16 — Split PDF + Chat Workspace

**Goal:** the signature view — PDF on the left, chat on the right, clicking a citation jumps to the page.

### Files to create
`src/app/chat/[id]/page.tsx`, `src/components/pdf-viewer/PdfPane.tsx`, `CitationLayer.tsx`, `src/components/chat/ChatPanel.tsx`, `Composer.tsx`, `src/components/ui/resizable.tsx` (shadcn) or a hand-rolled splitter.

### Steps
- **S16.01** `npm i @embedpdf/react-pdf-viewer` (verify the package's React 19 peer support; fallback `@cyntler/react-doc-viewer` or native `<iframe>` + `#page=` fragment — record the decision in §13).
- **S16.02** Layout: CSS grid `1fr 1fr` on `lg`, stacked tabs on mobile; left pane = `PdfPane`, right = `ChatPanel`; both panes scroll independently.
- **S16.03** `PdfPane`: loads the presigned MinIO URL for the selected document; page navigation state lifted to the page component so citations can command it
  (`pdfRef.current.goToPage(n)` + highlight overlay rectangle from the chunk's `char_start/char_end`-derived bounding box when available, else a page-level highlight banner).
- **S16.04** `ChatPanel`: message list (user right / assistant left), `CitationList` chips under assistant messages, composer with Enter-to-send, Shift+Enter newline, stop button while streaming, session id in the URL/query so history reloads.
- **S16.05** Document switcher inside the workspace (a select of the project's READY documents) so multi-document chat works without leaving the page.
- **S16.06** Accessibility/UX: `aria-live="polite"` on the streaming region, focus management on send, keyboard shortcuts `/` focus composer.
- **S16.07** ✔ CHECK open `/chat/demo`, load a PDF, ask a question, click a citation → the left pane jumps to the cited page and highlights; resize the window to mobile width → tabs switch correctly.
- **S16.08** Commit: `feat(frontend): add split pdf viewer and chat workspace with citation jump`.

### ✔ Acceptance Criteria
Citation → correct page navigation works; no hydration warnings; PDF renders for a 60-page file without freezing the UI.

---

## STAGE 17 — Chat Streaming UX & TTS Playback

**Goal:** render the agent thought timeline live, stream tokens, show citations, and play answers via TTS.

### Files to create
`src/hooks/useChat.ts`, `src/components/chat/ThoughtTimeline.tsx`, `TokenStream.tsx`, `CitationList.tsx`, TTS control inside `ChatPanel`.

### Steps
- **S17.01** `useChat.ts`: `messages`, `trace`, `citations`, `status: idle|streaming|error`, `send(query)`, `stop()`;
  wraps `streamPostSSE` with an `AbortController`; appends `token` deltas into the in-flight assistant message; appends `agent_state` into `trace` with timestamps; on `done` reconciles the final message id.
- **S17.02** `ThoughtTimeline.tsx`: collapsible vertical stepper with per-step spinner → check state and duration; maps `step` to icons/labels via a single `STEP_META` record (routing/expanding/retrieval/reranking/grading/generating/web_fallback/done) — keeps the UI vocabulary identical to the backend trace.
- **S17.03** `TokenStream.tsx`: renders streamed text with a caret while streaming; after completion, run a light markdown render (no raw HTML).
- **S17.04** `CitationList.tsx`: numbered `[1] Title · p.12` chips; click → callback to `PdfPane`; hover shows a snippet popover; "Copy citations" button.
- **S17.05** TTS: `useTts(text, voice)` — button per assistant message; fetch blob from `/tts`, `URL.createObjectURL`, `new Audio(url).play()`, revoke on unmount; show disabled state when the endpoint returns 503; voice selector from `/tts/voices`.
- **S17.06** Error UX: SSE `error` frame → toast + inline retry; `stop()` → keeps partial text and marks it partial.
- **S17.07** ✔ CHECK with `LLM_BACKEND=mock` (instant, deterministic) and with the real Groq key; confirm the timeline animates, tokens stream, stop works mid-stream, TTS audio plays.
- **S17.08** Commit: `feat(frontend): stream agent thought timeline, tokens, citations and tts playback`.

### ✔ Acceptance Criteria
All SSE event types render correctly; stop/abort works; TTS plays; no unhandled promise rejections; `npm run build` + `npm run lint` pass.

---

## STAGE 18 — Full-Stack Integration

**Goal:** one command brings up the entire platform; end-to-end verified.

### Steps
- **S18.01** Add to `docker-compose.yml`: `frontend` service (`build: ./frontend`, `ports: 3000:3000`, env `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`, depends_on api healthy), `api`, `worker`, plus a `profiles: [app]` guard already in place. Confirm api/worker share the same build context with different `target:`.
- **S18.02** Add `NEXT_PUBLIC_*` build-arg support in `frontend/Dockerfile` (`ARG NEXT_PUBLIC_API_URL` → `ENV`) because Next inlines `NEXT_PUBLIC_*` at build time.
- **S18.03** Networking: `NEXT_PUBLIC_API_URL` must be browser-reachable. Use `http://localhost:8000/api/v1` (host-published port) — **not** `http://api:8000`. Add a note in `.env.example`.
- **S18.04** `scripts/smoke_test.py` (runs from the api container, `httpx`): health → upload generated PDF → poll status to READY → chat stream (assert ≥1 `token` and a final `done`) → tts (skip if disabled) → delete → prints a pass/fail table and exits non-zero on failure.
- **S18.05** ✔ CHECK from a cold start: `docker compose down -v` then `docker compose --profile app up -d --build` then
  `docker compose run --rm api python scripts/smoke_test.py` → all steps pass; open `http://localhost:3000` and repeat the flow in the browser.
- **S18.06** `scripts/dev-up.ps1`, `dev-down.ps1`, `dev-logs.ps1` wrapping the common commands (PowerShell-friendly).
- **S18.07** Commit: `feat: wire full stack in compose and verify end-to-end ingestion and chat`.

### ✔ Acceptance Criteria
Single-command cold start works; smoke test green; browser flow identical to the API flow.

---

## STAGE 19 — Docs, Scripts & Polish

**Goal:** make the repo self-explanatory and reproducible for a fresh machine or agent.

### Steps
- **S19.01** Rewrite `README.md`: quickstart (prereqs, `.env`, compose up, URL), architecture diagram (reuse the ASCII art), pipeline description, API table, project structure, troubleshooting (models not downloading, ports busy, empty search results, TTS 503), and a **Build Progress** section pointing at `PLAN.md`.
- **S19.02** `docs/ARCHITECTURE.md`: data flow for ingestion and chat, sequence diagrams (mermaid), the RRF + grader + fallback decision logic, and the scaling story.
- **S19.03** `docs/API.md`: generated from OpenAPI (`docker compose run --rm api python -c "import json;..."` → save `docs/openapi.json`) plus a hand-written quick table.
- **S19.04** `scripts/seed_demo_pdf.py`: builds a 60-page PDF with headings, a multi-page table, and a planted sentence for retrieval tests; used by tests and manual demos.
- **S19.05** `scripts/query_probe.py` and `scripts/verify_index.py` (created in Stages 6–7; polish args/output here).
- **S19.06** ⛔ DECISION: Docling upgrade — add an optional `docling` extra + `CONTEXTA_PARSER=docling` branch in `parser.py`, guarded and default-off. Only if time allows; the PyMuPDF path must remain the default and stay tested.
- **S19.07** ⛔ DECISION: auth — v0.1 is intentionally unauthenticated with a client-supplied `project_id`. Document loudly in README ("not production-safe") and record in §13.
- **S19.08** Add `.github/workflows/ci.yml`: ruff + mypy + pytest on Python 3.12, and frontend `npm ci && npm run lint && npm run build`. ⛔ DECISION: repo may not be public/GitHub — if `git remote -v` is empty, keep the workflow file but note it is inert.
- **S19.09** Update `AGENTS.md` with the final command reference and the "read PLAN.md §3 tracker first" instruction.
- **S19.10** Commit: `docs: add developer runbook, scripts and architecture notes`.

### ✔ Acceptance Criteria
A fresh reader can go from clone to working stack using only `README.md`; all scripts run; CI config is syntactically valid.

---

## STAGE 20 — Final Verification & Release

**Goal:** prove the whole thing works, then tag it.

### Steps
- **S20.01** Clean-slate test: `docker compose down -v; docker system prune -f` (containers only, keep images), `docker compose --profile app up -d --build`, run smoke test, run backend tests, run frontend build.
- **S20.02** Full acceptance walkthrough against the README promises (tick each):
  1. Upload ack <200 ms ✔ (measure and record the number).
  2. 60-page PDF ingests without any HTTP timeout ✔.
  3. Layout-aware extraction incl. table markdown ✔.
  4. Parent/child chunking with table summaries ✔.
  5. Hybrid dense+BM25 retrieval ✔.
  6. FlashRank rerank ✔.
  7. Grader filters <70 ✔.
  8. Tavily fallback triggers when no chunk passes ✔ (verify with an intentionally unrelated question).
  9. SSE thought stream shows every step ✔.
  10. Citations jump to the right page ✔.
  11. TTS speaks the answer ✔.
- **S20.03** Record measured numbers in `docs/BENCHMARKS.md` (upload ack ms, ingest s/page, retrieval ms, rerank ms, first-token ms).
- **S20.04** Fix only release-blocking issues found in S20.02; each fix gets its own small commit (no mixed refactors).
- **S20.05** Mark every stage ✅ in §3, commit `chore: final verification, seed script and v0.1.0 tag`.
- **S20.06** Tag: `git tag -a v0.1.0 -m "Contexta Py v0.1.0"` and `git push --follow-tags` ⛔ only if the user asked to push; otherwise leave the tag local and say so.
- **S20.07** ✔ CHECK `git status` clean, `git log --oneline` shows one commit per stage (≥20 commits), `git tag` lists `v0.1.0`.

### ✔ Acceptance Criteria
All 11 README promises verified, ≥20 stage commits, clean tree, `v0.1.0` tagged.

---

## 6. Environment Variable Reference (complete)

`.env.example` must contain exactly these keys (grouped; `#` comments explain each):

```
# --- Core ---
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=<generate>
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000

# --- Postgres ---
POSTGRES_USER=contexta
POSTGRES_PASSWORD=change-me
POSTGRES_DB=contexta
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://contexta:change-me@postgres:5432/contexta

# --- Redis / Arq ---
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
ARQ_JOB_TIMEOUT=1800

# --- Qdrant ---
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=contexta_chunks
QDRANT_API_KEY=

# --- MinIO / S3 ---
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=contexta
MINIO_SECRET_KEY=change-me
MINIO_BUCKET=contexta
MINIO_SECURE=false

# --- Embeddings ---
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
EMBEDDING_DIM=768
EMBEDDING_BATCH_SIZE=32
EMBEDDING_BACKEND=fastembed      # fastembed | hash
MODEL_CACHE_DIR=/models

# --- Parser / chunking ---
PARSER=pymupdf                   # pymupdf | docling
CHUNK_PARENT_SIZE=2000
CHUNK_CHILD_SIZE=400
CHUNK_CHILD_OVERLAP=60

# --- Retrieval ---
RETRIEVAL_CANDIDATES=40
RETRIEVAL_TOP_K=8
RERANK_TOP_K=5
RERANK_MIN_SCORE=0.0
RERANK_MODEL=ms-marco-MiniLM-L-12-v2
GRADER_THRESHOLD=70

# --- LLM (Groq via OpenAI SDK) ---
GROQ_API_KEY=
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1500
LLM_BACKEND=groq                 # groq | mock

# --- Web search ---
TAVILY_API_KEY=
WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=5

# --- TTS ---
TTS_ENABLED=true
TTS_VOICE=en-US-AriaNeural

# --- Ingestion ---
WORKER_DISPATCH_ENABLED=true
MODEL_DOWNLOAD_ON_STARTUP=true
```

Frontend `.env.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_PROJECT_ID=00000000-0000-0000-0000-000000000000
```

---

## 7. Conventions

- Python: 4-space indent, `ruff` formatted, type hints on public functions, `async` everywhere I/O-bound; no blocking calls inside coroutines (use `asyncio.to_thread`).
- Module names `snake_case`, classes `PascalCase`, Pydantic models `*In`/`*Out`.
- Every FastAPI route has `response_model` and explicit status codes.
- All backend exceptions are converted to `{"error": {"code", "message", "request_id"}}` in `app/core/errors.py`.
- Frontend: TypeScript `strict`, no `any`, shadcn primitives for all UI, `"use client"` only where interactivity demands it.
- Commit format: `<type>(<scope>): <lowercase imperative summary>`, types `feat|fix|chore|test|docs|refactor|infra`.
- Never commit: `.env`, model caches, node_modules, build output, uploads.

---

## 8. Test Matrix (what "done" means per layer)

| Layer | How verified | Command |
| :--- | :--- | :--- |
| Unit (chunk/rrf/rerank/graph) | pytest + mocks, no network | `docker compose run --rm api pytest -q` |
| Integration (API + DB + fakes) | pytest with ASGI transport | `docker compose run --rm api pytest tests/test_documents_api.py -q` |
| Contract (SSE order) | pytest asserting event sequence | `docker compose run --rm api pytest tests/test_sse.py -q` |
| Manual backend | curl transcript | `scripts/smoke_test.py` |
| Frontend | build + lint + manual checklist §16/§17 | `npm run lint; npm run build` |
| End-to-end | cold start + smoke | `docker compose --profile app up -d --build` then smoke test |

---

## 9. API Surface (authoritative — frontend must match)

```
GET    /api/v1/health
GET    /api/v1/health/ready
POST   /api/v1/documents                      (multipart) -> 202 {job_id, document_id, status}
GET    /api/v1/documents?project_id=
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/file    -> 302 presigned
POST   /api/v1/documents/{document_id}/retry   -> 202 (Stage 19)
GET    /api/v1/documents/events               (SSE status stream)
POST   /api/v1/chat/stream                    (SSE thought stream)
GET    /api/v1/chat/history/{session_id}
DELETE /api/v1/chat/history/{session_id}
POST   /api/v1/tts                            -> audio/mpeg stream
GET    /api/v1/tts/voices
```

---

## 10. Definition of Done (per stage)
1. All step IDs in the stage completed.
2. Acceptance criteria pass with pasted command output.
3. `docker compose ps` shows no unhealthy service (for infra stages).
4. `ruff`, `mypy`, `pytest` green (for backend stages 12+).
5. `npm run lint && npm run build` green (for frontend stages 13+).
6. §3 tracker row marked ✅.
7. Stage commit created — and only that commit for that stage.

---

## 11. Performance Budgets (targets to hit; record actuals in Stage 20)

| Metric | Target |
| :--- | :--- |
| Upload ack (202 response) | < 200 ms |
| Ingestion throughput | ≥ 1 page / 2 s (CPU-bound, batched) |
| Embedding batch (32 chunks) | < 1.5 s |
| Hybrid retrieval (RRF, 40 candidates) | < 400 ms |
| FlashRank rerank (20 candidates, warm) | < 50 ms |
| Grader (20 chunks, concurrent) | < 2 s |
| Time to first SSE token | < 2.5 s |
| PDF pane scroll/zoom | 60 fps on a 60-page doc |

---

## 12. Open Risks & Mitigations (live list)

| # | Risk | Mitigation | Stage |
| :--- | :--- | :--- | :--- |
| R1 | Python 3.14 host breaks ML wheels | Run backend only in `python:3.12-slim` containers | 1–3 |
| R2 | Docker daemon not running / not installed | S01.01 starts/validates Docker Desktop first | 1 |
| R3 | fastembed/flashrank model downloads (~530 MB) need internet | Cache dir volume; `EMBEDDING_BACKEND=hash` fallback | 6, 8 |
| R4 | `flashrank`/`onnxruntime` wheel mismatch on slim | Pin `onnxruntime==1.19.2` | 8 |
| R5 | `langgraph` API drift | Pin `0.2.60`; documented `ainvoke` fallback | 9 |
| R6 | SSE buffering through proxies/Next dev server | `X-Accel-Buffering: no`, `no-cache`, heartbeat, fetch-streaming client (no EventSource buffering) | 10 |
| R7 | Host ports 5432/6379 already taken | Change host-side mapping only | 2 |
| R8 | Qdrant sparse BM25 model unavailable offline | Hand-rolled hashing sparse fallback | 6 |
| R9 | Docling drags in torch (~2 GB) | PyMuPDF default; Docling opt-in extra | 5, 19 |
| R10 | `@embedpdf/react-pdf-viewer` React 19 peer conflict | Fall back to native iframe with `#page=` | 16 |
| R11 | Next inlines `NEXT_PUBLIC_*` at build time | `ARG`/`ENV` in `frontend/Dockerfile`; use `localhost:8000` not `api:8000` | 18 |
| R12 | Tavily/edge-tts need outbound internet | Feature flags `WEB_SEARCH_ENABLED`, `TTS_ENABLED` with graceful degradation | 9, 11 |
| R13 | No authentication in v0.1 | Documented explicitly as non-production; project_id is a plain UUID | 4, 19 |
| R14 | Long PDFs → memory pressure in worker | Stream page-by-page, batch embeddings, `job_timeout=1800`, `max_jobs=2` | 5, 6 |
| R15 | Windows CRLF breaks shell scripts in containers | `.gitattributes` forces LF; scripts mounted read-only | 1 |

---

## 13. Decision Log (append-only — record every deviation here)

| Date | Stage | Decision | Rationale |
| :--- | :--- | :--- | :--- |
| 2026-10-05 | Plan | Backend runs 100% in Docker (`python:3.12-slim`) | Host has no 3.12; 3.14 lacks ML wheels |
| 2026-10-05 | Plan | PyMuPDF primary parser, Docling optional | Avoids torch in the default image |
| 2026-10-05 | Plan | Qdrant single collection with `dense` + `bm25` named vectors, server-side RRF | Matches README; one round trip |
| 2026-10-05 | Plan | SSE via `fetch` streaming, not `EventSource` | `EventSource` cannot POST a JSON body |
| 2026-10-05 | Plan | v0.1 is unauthenticated, `project_id` client-supplied | Scope control; flagged non-production |
| 2026-10-05 | S01.01 | Docker Desktop is at `C:\Users\USER\AppData\Local\Programs\DockerDesktop\`, **not** the default `C:\Program Files\Docker\Docker\` | `Test-Path` on the default path returned False; engine verified `29.8.0 / linux` |
| 2026-10-05 | S02.05 | `minio/minio` and `minio/mc` are **unpullable** in this environment (Docker Hub returns `pull access denied`; `quay.io/minio/*` returns 401). Replaced with **`rustfs/rustfs:latest`**, which speaks the same S3/MinIO API | Verified: bucket created and presigned URLs validate through the boto3 SigV4 round trip |
| 2026-10-05 | S02.05 | `createbuckets` is a `python:3.12-slim` one-shot that pip-installs `boto3` and runs `infra/minio/createbuckets.py`, instead of a `mc` client container | No MinIO-family image is available to run `mc`; also removes the shell dependency |
| 2026-10-05 | S02.08 | Added `MINIO_PUBLIC_ENDPOINT=http://localhost:9000` | Presigned URLs are signed against the Host header, so signing with the internal `http://minio:9000` would produce a URL the browser cannot resolve or validate |
| 2026-10-05 | S03.01 | Dependency pins **generated from a verified install**, not hand-written. `requirements.in` holds direct deps; `requirements.txt` is the full resolved freeze. Resolved set has **no torch** (fastembed 0.8.1 is ONNX-only) | Removes guesswork; the image stays small. Key versions: fastapi 0.142.2, sqlalchemy 2.1.3, **langgraph 1.2.12**, langchain-core 1.6.6, pymupdf4llm 1.28.2, qdrant-client 1.19.1, fastembed 0.8.1, openai 3.24.0 |
| 2026-10-05 | S03.03 | `backend/Dockerfile` is one dependency layer with thin `api` / `worker` targets (not separate dependency sets) | Both services share an identical pip layer, so one build serves both |
| 2026-10-05 | S03.03 | `pyproject.toml` must be `COPY`d into the image | Without it `ruff`/`mypy`/`pytest` run with library defaults inside the container, silently ignoring the project's rules |
| 2026-10-05 | S03.04 | List-valued settings use `Annotated[list[str], NoDecode]` | pydantic-settings JSON-decodes complex types in the *source* layer, before field validators run, so `a,b,c` raised `SettingsError` |
| 2026-10-05 | S03.05 | `StorageClient` builds a **fresh** aioboto3 client per operation | `session.client(...)` returns a single-use context manager; caching it produced `cannot reuse already awaited coroutine` |
| 2026-10-05 | S03.08 | Request-id/timing middleware is **raw ASGI**, not `BaseHTTPMiddleware` | The base class adds a task-queue hop that delays the first frame of a long-lived SSE stream |
| 2026-10-05 | S03.06 | Enums use `enum.StrEnum`; `pyproject.toml` ruff config copied into image | `UP042` + correct `str()` behaviour, and project lint rules now actually apply |
| 2026-10-05 | S03.06 | `ChatMessage` gained `session_id`, `trace`, `model`; `Document` gained `chunk_count`, `job_id`, `size_bytes`, `content_type` | The chat history/TTS endpoints address turns by `session_id`; `trace` backs the agent timeline UI |
| 2026-10-05 | S04.01 | **API host port moved 8000 → 8010** (`API_PORT=8010`) | An unrelated Python service on this machine already listens on host port 8000 (a catalog/quotes/tools API). It is not ours, so it was left untouched. Symptom was a confusing `{"detail":"Not Found"}` 404 from the wrong service |
| 2026-10-05 | S04.01 | Arq log line uses `RedisSettings.host/port` | arq 0.28's `RedisSettings` has no `queue_name`, and `ArqRedis` has neither `name` nor `redis_name` |
| 2026-10-05 | S04.04 | `POST /documents` takes `project_id` as an explicit **Form** field; the `ProjectDep` dependency (query/header) is used by the non-body routes | The shared dependency cannot see multipart form fields, so an upload without the query param 422'd |
| 2026-10-05 | S04.04 | `GET /documents/{id}/file` returns **302** (not 307) | Matches the documented API surface exactly |
| 2026-10-05 | S04.06 | Added `scripts/seed_demo_pdf.py` and `./data` + `./scripts` volume mounts | Stage 4's acceptance test needs a real PDF; PyMuPDF 1.28 requires `pymupdf.Point`, not `(x, y)` tuples |

_(Add one row each time a plan step is deviated from — this is what makes the plan recoverable.)_

---

## 14. Quick Command Reference

```powershell
# start / stop everything
docker compose --profile app up -d --build
docker compose --profile app logs -f api worker
docker compose down -v

# backend one-offs
docker compose run --rm api alembic upgrade head
docker compose run --rm api pytest -q
docker compose run --rm api ruff check .
docker compose run --rm api mypy app
docker compose run --rm api python scripts/smoke_test.py

# frontend
cd frontend; npm ci; npm run dev; npm run lint; npm run build

# state inspection
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:6333/collections
docker compose exec postgres psql -U contexta -d contexta -c "\dt"
```

<!-- END OF PLAN -->