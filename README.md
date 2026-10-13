# 📋 Contexta Py — High-Performance Python-Native Multi-Agent RAG Platform

## 📋 Project Overview

**Contexta Py** is an enterprise-grade, asynchronous, multi-agent AI document interaction platform engineered specifically with a **Python backend (FastAPI + LangGraph)** and a **Next.js frontend**. Built to overcome the execution timeout limits, single-threaded bottlenecks, and naive text parsing inherent in Node.js RAG setups, Contexta Py features background worker ingestion queues, layout-aware PDF parsing (tables, multi-column, OCR), parallelized hybrid search, and streaming agent execution traces via Server-Sent Events (SSE).

---

## 🏗 Architecture

The platform operates on a decoupled architecture separating the **UI / Presentation Layer**, the **Async API & Agent Service**, and the **Distributed Background Queue**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Next.js 16)                        │
│  ┌───────────────┐  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │ Landing / UI  │  │ Dashboard / CRUD │  │ Split PDF + Chat View   │  │
│  └───────────────┘  └──────────────────┘  └─────────────────────────┘  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTPS / REST / SSE (Streaming)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                   API LAYER (FastAPI - Async Python)                  │
│  ┌────────────────────────┐ ┌──────────────────────┐ ┌──────────────┐  │
│  │ /api/v1/chat/stream    │ │ /api/v1/documents    │ │ /api/v1/tts  │  │
│  │ (SSE Thought Stream)   │ │ (Async Upload Queue) │ │ (Edge-TTS)   │  │
│  └────────────────────────┘ └──────────────────────┘ └──────────────┘  │
└──────────────┬───────────────────────────────────────────┬─────────────┘
               │ Dispatch Job                              │ Direct State Execution
┌──────────────▼──────────────────────────┐    ┌───────────▼─────────────┐
│ BACKGROUND INGESTION WORKER (Arq/Redis) │    │ LANGGRAPH AGENT ENGINE  │
│ ┌─────────────────────────────────────┐ │    │ ┌─────────────────────┐ │
│ │ 1. Docling Layout & Table Parsing   │ │    │ │ Manager / Router    │ │
│ │ 2. Parent-Child Chunking            │ │    │ ├─────────────────────┤ │
│ │ 3. Batch Embeddings (HuggingFace)   │ │    │ │ Parallel MultiQuery │ │
│ │ 4. Hybrid Indexing (Vector + BM25)  │ │    │ ├─────────────────────┤ │
│ └─────────────────────────────────────┘ │    │ │ Hybrid Search &     │ │
└──────────────────┬──────────────────────┘    │ │ FlashRank Reranker  │ │
                   │                           │ ├─────────────────────┤ │
                   │                           │ │ Async Grader Agent  │ │
                   │                           │ ├─────────────────────┤ │
                   │                           │ │ Web Fallback Agent  │ │
                   │                           │ ├─────────────────────┤ │
                   │                           │ │ Generator Agent     │ │
                   │                           │ └─────────────────────┘ │
                   │                           └───────────┬─────────────┘
┌──────────────────▼───────────────────────────────────────▼─────────────┐
│                           DATA & STORAGE LAYER                          │
│  ┌─────────────────────────┐ ┌─────────────────┐ ┌───────────────────┐  │
│  │ Qdrant / Atlas VectorDB │ │ PostgreSQL      │ │ S3 / MinIO Store  │  │
│  │ (Dense + Sparse BM25)   │ │ (Relational DB) │ │ (PDF Files)       │  │
│  └─────────────────────────┘ └─────────────────┘ └───────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```
[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/kashifali-it/contexta?utm_source=readme&utm_medium=badge)
---

## 🧩 Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Backend Framework** | FastAPI (Async Python 3.12, Pydantic v2) |
| **Agent Framework** | LangGraph (Python native graph state machine) |
| **Task Queue / Worker** | Arq (Async Redis-based task queue) + Redis |
| **PDF & Layout Parser** | Docling / PyMuPDF (Vision & structural layout parsing) |
| **Text Chunking** | Parent-Child / Hierarchical & Semantic Chunkers |
| **Vector Database** | Qdrant / MongoDB Atlas (Dense Vectors + Sparse BM25) |
| **Embeddings** | Hugging Face (`BAAI/bge-base-en-v1.5`) / FastEmbed |
| **Reranking Engine** | FlashRank (Ultra-fast local ONNX) / Jina AI Reranker v3 |
| **LLM Provider / Engine** | Groq (Llama 3.3 70B / Mixtral) via OpenAI Python SDK |
| **Web Search API** | Tavily Search API |
| **Frontend Framework** | Next.js 16 (App Router), TypeScript 5 |
| **UI & Styling** | React 19, Tailwind CSS 4, shadcn/ui |
| **PDF Viewer** | `@embedpdf/react-pdf-viewer` |
| **Text-to-Speech** | `edge-tts` (Microsoft Edge Neural Voices) |

---

## 🔄 Workflow & Pipeline Breakdown

### 1. Asynchronous Document Ingestion Pipeline
To prevent standard 10–30 second HTTP execution timeouts on large PDFs:

1. **Instant Upload Ack:** User drops a PDF in Next.js $
ightarrow$ FastAPI creates a `Document` record with status `PROCESSING` and returns a `job_id` immediately ($<200	ext{ms}$).
2. **Background Ingestion Worker (Arq/Redis):**
   * **Layout-Aware Extraction:** Docling extracts document hierarchy, headers, reading order, and complex tables cleanly into structured Markdown.
   * **Hierarchical (Parent-Child) Chunking:** Large parent chunks ($2000$ chars) preserve context, while smaller child chunks ($400$ chars) are embedded for high-precision retrieval.
   * **Table Summarization:** Structural tables get LLM-generated summaries to improve semantic vector lookup.
   * **Batch Embeddings:** Hugging Face embedding model embeds child chunks asynchronously in parallel batches.
   * **Dual Indexing:** Stores dense vectors and sparse keyword tokens into vector storage.
3. **Completion Event:** Worker updates document state to `READY` and triggers a WebSocket/SSE notification to update the frontend.

---

### 2. Parallelized Agentic RAG Flow (LangGraph)

When a question arrives, a high-speed execution graph processes the request:

```
[ User Query ]
      │
      ▼
┌───────────────┐
│ Manager Router│ ─── (General / Personal) ───► Direct Stream
└───────┬───────┘
        │ (Document Question)
        ▼
┌──────────────────┐
│ Parallel Agent   │ ──► Generates 3 Queries concurrently via asyncio.gather()
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ Hybrid Retrieval │ ──► Concurrent Dense + BM25 Search across child chunks
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ FlashRank Rerank │ ──► Local ONNX reranking filters top-K chunks
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ Async Grader     │ ──► Concurrent evaluation; discards chunks scoring < 70
└───────┬──────────┘
        │
   ┌────┴────────────────────────┐
   │ (Valid Chunks ≥ 70)         │ (No Valid Chunks)
   ▼                             ▼
┌──────────────────┐         ┌──────────────────────┐
│ Generator Agent  │         │ Web Search Fallback  │
│ (Answer + Pages) │         │ (Tavily Query Engine)│
└──────────────────┘         └──────────────────────┘
```

1. **Manager Router:** Classifies question intent.
2. **Parallel Query Expansion:** Executes 3 multi-query variations in parallel using Python's `asyncio.gather()`, cutting retrieval latency by 60%.
3. **Hybrid Search + Reciprocal Rank Fusion (RRF):** Merges vector similarity scores with BM25 keyword matching.
4. **Local ONNX Reranking:** FlashRank re-ranks candidates in $<15	ext{ms}$ on CPU.
5. **Async Relevance Grader:** Evaluates candidate chunks concurrently for truthfulness and context alignment.
6. **Streaming Generator:** Streams answer tokens and precise page citations via Server-Sent Events (SSE).

---

## ⚡ Real-Time Thought Stream (Server-Sent Events)

Instead of keeping the user waiting in silence during multi-agent execution, FastAPI streams step-by-step progress events over SSE:

```json
data: {"event": "agent_state", "step": "routing", "message": "Analyzing query intent..."}
data: {"event": "agent_state", "step": "expanding", "message": "Generated 3 search variants..."}
data: {"event": "agent_state", "step": "retrieval", "message": "Retrieved 12 candidate chunks..."}
data: {"event": "agent_state", "step": "grading", "message": "4 chunks passed relevance threshold (Score: 88%)"}
data: {"event": "token", "content": "According to page 12 of the document..."}
```

---

## 🗄 Data Models (SQLAlchemy 2.0 / Pydantic v2)

### `Document`
* `id`: UUID (Primary Key)
* `title`: String
* `file_url`: String
* `status`: Enum (`PENDING`, `PROCESSING`, `READY`, `FAILED`)
* `project_id`: UUID (Foreign Key)
* `page_count`: Integer
* `created_at`: DateTime

### `DocumentChunk`
* `id`: UUID
* `document_id`: UUID (Foreign Key)
* `parent_chunk_id`: UUID (Optional)
* `content`: Text
* `summary`: Text (Optional, for tables/figures)
* `page_number`: Integer
* `is_table`: Boolean
* `embedding_id`: String (Vector DB reference ID)

### `ChatMessage`
* `id`: UUID
* `project_id`: UUID
* `role`: Enum (`USER`, `ASSISTANT`)
* `content`: Text
* `citations`: JSONB (List of document IDs, page numbers, and chunk texts)
* `created_at`: DateTime

---

## 📁 Project Directory Structure

```
Contexta-py/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/             # REST & SSE API Routers
│   │   │   ├── v1/
│   │   │   │   ├── chat.py
│   │   │   │   ├── documents.py
│   │   │   │   └── tts.py
│   │   ├── core/            # Config, DB connections, Security
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── agents/          # LangGraph Multi-Agent Workflows
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   └── nodes/
│   │   │       ├── router.py
│   │   │       ├── search.py
│   │   │       ├── grader.py
│   │   │       ├── generator.py
│   │   │       └── web_fallback.py
│   │   ├── services/        # Ingestion, Parsers, Rerankers
│   │   │   ├── ingestion.py
│   │   │   ├── parser.py    # Docling layout parsing
│   │   │   ├── hybrid_db.py # Vector + BM25 engine
│   │   │   └── reranker.py  # FlashRank / Jina engine
│   │   └── workers/         # Arq Background Jobs
│   │       └── tasks.py
│   ├── requirements.txt
│   └── main.py
│
├── frontend/                 # Next.js 16 UI
│   ├── src/
│   │   ├── app/             # App router pages
│   │   │   ├── dashboard/
│   │   │   └── chat/[id]/
│   │   ├── components/      # Split viewer, annotations, chat UI
│   │   │   ├── pdf-viewer/
│   │   │   └── chat/
│   │   └── lib/             # SSE & API clients
│   └── package.json
└── docker-compose.yml        # FastAPI, Redis, Qdrant, Postgres
```

---

## 🚀 Architectural Advantages over Node.js RAG

| Key Capability | Node.js / Next.js API Routes | Python (FastAPI + LangGraph) |
| :--- | :--- | :--- |
| **Ingestion Latency** | Synchronous execution easily triggers serverless 10–30s timeouts. | Asynchronous background workers (Arq/Redis) process 100+ page PDFs safely without blocking APIs. |
| **PDF Layout Quality** | Basic text extractors (`pdf-parse`) fail on tables, multi-column text, and scans. | Layout-aware parsers (`Docling`, `PyMuPDF`) extract clean structured tables and reading orders. |
| **Agent Execution Speed** | Async operations run single-threaded in Node.js event loop. | Native `asyncio.gather()` executes query expansions, hybrid searches, and graders concurrently. |
| **Reranking Overhead** | Relies entirely on external API calls (adding 200–500ms network latency). | Supports ultra-fast local ONNX models (`FlashRank`) in $<15	ext{ms}$ directly in-memory. |
| **User Transparency** | Black-box streaming where user waits for final text. | Granular SSE Event Stream publishing real-time agent reasoning steps. |

%% Generated by https://gitdiagram.com/kashifali-it/contexta
flowchart TD

subgraph group_api["API and documents"]
  node_client["Next.js client"]
  node_document_api["Document API<br/>[documents.py]"]
  node_api_router["API router<br/>[router.py]"]
end

subgraph group_ingest["Ingestion pipeline"]
  node_worker["Ingestion worker<br/>[tasks.py]"]
  node_ingestion["Ingestion service<br/>[ingestion.py]"]
  node_pdf_parser["PDF parser<br/>[parser.py]"]
  node_chunker["Chunker<br/>[chunker.py]"]
  node_llm["LLM client<br/>[llm.py]"]
end

subgraph group_rag["Agentic Q&amp;A"]
  node_agent_engine["Agent engine"]
  node_hybrid_search["Hybrid retrieval"]
  node_grader["Relevance grader"]
  node_answer["Answer generator"]
  node_web_search["Web fallback"]
  node_tts["Text-to-speech"]
end

subgraph group_state["State and storage"]
  node_postgres[("PostgreSQL")]
  node_redis["Redis queue"]
  node_object_store[("Object storage<br/>[storage.py]")]
  node_vector_store[("Vector store")]
  node_tavily["Tavily search"]
  node_edge_tts["Edge TTS"]
end

node_user(("User"))

node_user -->|"uploads PDF"| node_client
node_client -->|"sends request"| node_document_api
node_api_router -->|"registers routes"| node_document_api
node_document_api -->|"stores file"| node_object_store
node_document_api -->|"creates record"| node_postgres
node_document_api -->|"enqueues job"| node_redis
node_worker -->|"runs ingestion"| node_ingestion
node_ingestion -->|"fetches file"| node_object_store
node_ingestion -->|"parses document"| node_pdf_parser
node_ingestion -->|"creates chunks"| node_chunker
node_ingestion -->|"summarizes tables"| node_llm
node_ingestion -->|"updates status"| node_postgres
node_user -.->|"asks question"| node_agent_engine
node_agent_engine -.->|"dispatches retrieval"| node_hybrid_search
node_hybrid_search -.->|"searches chunks"| node_vector_store
node_agent_engine -.->|"checks relevance"| node_grader
node_grader -.->|"passes relevant chunks"| node_answer
node_grader -.->|"falls back"| node_web_search
node_answer -.->|"streams answer"| node_client
node_client -.->|"requests speech"| node_tts
node_tts -.->|"generates audio"| node_edge_tts
node_web_search -.->|"searches web"| node_tavily

click node_client "https://github.com/kashifali-it/contexta/tree/main/frontend"
click node_document_api "https://github.com/kashifali-it/contexta/blob/main/backend/app/api/v1/documents.py"
click node_api_router "https://github.com/kashifali-it/contexta/blob/main/backend/app/api/v1/router.py"
click node_worker "https://github.com/kashifali-it/contexta/blob/main/backend/app/workers/tasks.py"
click node_ingestion "https://github.com/kashifali-it/contexta/blob/main/backend/app/services/ingestion.py"
click node_pdf_parser "https://github.com/kashifali-it/contexta/blob/main/backend/app/services/parser.py"
click node_chunker "https://github.com/kashifali-it/contexta/blob/main/backend/app/services/chunker.py"
click node_llm "https://github.com/kashifali-it/contexta/blob/main/backend/app/services/llm.py"
click node_agent_engine "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_hybrid_search "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_grader "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_answer "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_web_search "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_tts "https://github.com/kashifali-it/contexta/tree/main/backend/app/agents/nodes"
click node_object_store "https://github.com/kashifali-it/contexta/blob/main/backend/app/services/storage.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_client,node_document_api,node_api_router,node_user toneBlue
class node_worker,node_ingestion,node_pdf_parser,node_chunker,node_llm toneAmber
class node_agent_engine,node_hybrid_search,node_grader,node_answer,node_web_search,node_tts toneMint
class node_postgres,node_redis,node_object_store,node_vector_store,node_tavily,node_edge_tts toneRose
