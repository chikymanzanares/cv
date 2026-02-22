
# Chatbot SSE API

A minimal FastAPI service implementing a **Run-based execution model** with **Server-Sent Events (SSE)** streaming and **PostgreSQL persistence**.

The system is organized using **Domain / Application / Infrastructure** layers and the **Repository pattern**, so the database engine can be swapped without changing business logic.

---

## Architecture

```
app/
  domain/
    chat/
      entities.py
      repositories/
  application/
    chat/
      create_user.py
      create_thread.py
      post_message_create_run.py
      cancel_run.py
      run_executor.py
  infrastructure/
    db/
    models/
    repositories/
    web/
      routers/
```

- **Domain**: business entities and repository interfaces
- **Application**: use cases (no framework code)
- **Infrastructure**: FastAPI, SQLAlchemy, Postgres, SSE

Runs produce events that are:
1. Stored in Postgres (`run_events`)
2. Streamed via SSE (`/api/runs/{run_id}/events`)

Clients can reconnect using `Last-Event-ID` to resume the stream.

---

## Key directories

- **`cv_generation/`** — Offline pipeline to generate synthetic CVs (JSON + HTML + PDF) using an LLM and WeasyPrint. Produces the dataset under `cv_generation/data/cvs/`. See [cv_generation/README.md](cv_generation/README.md) for folder structure and commands.

- **`rag/`** — RAG pipeline: index CV PDFs (FAISS + BM25) and run semantic + keyword search. Shared logic lives in `rag/retrieval.py` (used by CLI and API). See [rag/README.md](rag/README.md) for indexing, retrieval, and reranking details.

- **`front/`** — React + Vite + Tailwind chat interface. Streams LLM responses token-by-token via SSE. See [front/README.md](front/README.md) for structure and tech details.

---

## Requirements

- Docker
- Docker Compose
- Make

---

## Configuration

1. **Copy the environment template** and create your local `.env`:

   ```
   cp .env_ex .env
   ```

2. **Set your API keys** in `.env` according to the LLM provider you use:

   - **Anthropic:** set `LLM_PROVIDER=anthropic` and add your key:
     ```
     ANTHROPIC_API_KEY=your-key-here
     ```
   - **Google (Gemini):** set `LLM_PROVIDER=google` and add:
     ```
     GEMINI_API_KEY=your-google-api-key-here
     ```

Without a valid `.env` and the corresponding API key, the project will not work.

---

## Start the project

### First time (or after regenerating CVs)

**Step 1 — Generate CVs + PDFs + RAG index** in one command:

```bash
make dataset
```

This runs sequentially:
- `gen-all` → generates 30 fake CV JSON files and renders them to PDF
- `rag-rebuild` → extracts text from the PDFs and builds the FAISS + BM25 search indices

The first run downloads the embedding model ([intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small), ~117 MB, cached after that).

> **Important:** every time you regenerate the CVs (`make gen-all` or `make dataset`), you must rebuild the RAG index — otherwise the API will answer from stale data. `make dataset` always does both in the correct order.

**Step 2 — Start the API, frontend and database:**

```bash
make up
```

This builds images, starts Postgres, runs Alembic migrations, starts FastAPI on http://localhost:8000 and the frontend on http://localhost:5173.

---

### Subsequent starts (no CV changes)

```bash
make up
```

The RAG index in `rag_store/` is already built and persisted on disk. The API loads it into memory at startup automatically.

---

### Regenerating the dataset later

```bash
make dataset
docker compose restart api
```

`make dataset` rebuilds CVs and the index. The API restart forces it to load the new index from disk (the running instance keeps the old one in memory until restarted).

---

## API Documentation

Open:
- Swagger UI: http://localhost:8000/docs
- OpenAPI:   http://localhost:8000/openapi.json

---

## Minimal Example Flow

### 1. Create a user

```
curl -X POST http://localhost:8000/api/users   -H "Content-Type: application/json"   -d '{"name":"smoke-user"}'
```

Response:

```
{"user_id":1,"name":"smoke-user"}
```

---

### 2. Create a thread

```
THREAD_ID=$(curl -s -X POST http://localhost:8000/api/threads   -H "Content-Type: application/json"   -d '{"user_id": 1}'   | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])")

echo "THREAD_ID=$THREAD_ID"
```

---

### 3. Post a message (creates a run)

```
RUN_ID=$(curl -s -X POST http://localhost:8000/api/threads/$THREAD_ID/messages   -H "Content-Type: application/json"   -d '{"content":"hello"}'   | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])")

echo "RUN_ID=$RUN_ID"
```

---

### 4. Get run status

```
curl http://localhost:8000/api/runs/$RUN_ID
```

---

### 5. Stream events (SSE)

```
curl -N http://localhost:8000/api/runs/$RUN_ID/events
```

---

### 6. Resume from last event

```
curl -N http://localhost:8000/api/runs/$RUN_ID/events   -H "Last-Event-ID: 10"
```

---

### 7. Cancel a run

```
curl -X POST http://localhost:8000/api/runs/$RUN_ID/cancel
```

---

### 8. Inspect persisted events in Postgres

```
docker compose exec postgres psql -U chatbot -d chatbot -P pager=off -c "select seq, type, data from run_events where run_id='${RUN_ID}' order by seq;"
```

---

## Chat flow (schema)

- **Open chat:** Front → `POST /api/users`, `POST /api/threads` → Postgres (insert user, thread). Session per request, then closed. Front stores `thread_id` in localStorage, goes to `/chat`.

- **Send message:** Front → `POST .../messages` with `content` → API writes user message + creates run in Postgres, returns `run_id`, starts background task. Request session closed; background opens one new session for the run.
- **Streaming (SSE):** Front opens `GET /api/runs/{run_id}/events`. Backend polls Postgres every ~0.35 s (new session per poll), reads new `run_events`, sends SSE frames; when run is done, closes stream. Tokens are written by the executor to `run_events`; SSE only reads from DB.
- **Backend run:** One DB session for whole run: load thread messages → RAG search → LLM stream; each token → append to `run_events`; at end → `final` event, insert assistant message, run status `done`. Then session closed.
- **Front with response:** Token events → append to bubble; `final` → full text + sources; `done` → close stream.
- **Follow-up:** Same thread_id; new message → new run. Executor loads `list_messages(thread_id)` → gets previous user + assistant + new user; LLM receives that history + RAG, so context comes from Postgres.


---

## improvements (and next steps)

### RAG improvements

- **Contextual chunking**: Use an LLM to parse each CV and split it into structured sections (e.g. experience, technologies, education). Chunk by section instead of fixed character windows so retrieval can target specific parts (e.g. "experience" or "skills"). Implement with Pydantic schemas and Instructor (or similar) for structured LLM output.

### Chat improvements

- **Query normalization**: Use a small LLM (e.g. a "mini" model, possibly local) to normalize and improve user questions before sending them to the main RAG/LLM pipeline. This can also enable caching: repeated or equivalent questions can be served from cache instead of calling the main model.
- **Database indexes**: Review and add indexes to keep chat queries fast as data grows (e.g. `run_events(run_id, seq)` for SSE polling, `messages(thread_id, created_at)` for thread history, `runs(thread_id, status)` for run lookup). Align with actual query patterns and migration tooling (e.g. Alembic).
**SSE and polling:** Polling Postgres for new events is a simple, durable approach (no extra infra; replay and multi-pod work out of the box). It is not the only option: **improvements** could include Postgres `LISTEN/NOTIFY` so the SSE loop only wakes when new events are written (fewer empty polls), or an in-memory/Redis channel between executor and SSE handler for lower latency (at the cost of durability and cross-pod replay unless events are also persisted).

### CV generation

- **Improve variability**: Use more prompt types and templates to generate CVs; combine different models (e.g. one for structure, another for tone). Increase the number of styles and, optionally, add a second model that post-processes the generated text to change style or expand sections (e.g. elaborate on experience, vary wording).

---

## Technical decisions

- **Why LangGraph and LangChain were not used**: The current execution model is kept simple and explicit (single run, linear flow: load history → RAG → LLM stream → persist). LangGraph/LangChain would add abstraction and dependency weight without a current need for multi-step graphs or tool-calling frameworks; the contract in [AGENTS.md](../AGENTS.md) is already designed so that a future swap to LangGraph or other executors does not change client behavior (SSE, RunEvents, persistence).

- **Chat UX and scope**: The chat is intentionally minimal and improvable. Further improvements (e.g. suggested questions, filters, UX refinements) should be driven by real usage and user feedback so the product does not over-engineer in multiple directions without validation.

### Tools left out of scope (proof of concept)

The following were deliberately excluded for practical reasons as this is a technical exercise; they would be required or recommended for a production-ready product:

- **Security and access**: Authentication, authorization, and login (e.g. OAuth2, JWT, session management). No user identity or access control beyond a simple user/thread association.
- **Observability**: Structured logging, metrics (e.g. Prometheus), tracing (e.g. OpenTelemetry), and alerting. For AI-specific observability, tools such as **LangSmith**, **Phoenix (Arize)**, or **Weights & Biases** could be used to trace LLM calls, latency, token usage, and prompt/response quality.
- **Testing**: Integration tests (e.g. API + DB + SSE replay, or end-to-end with a real RAG index). Only manual verification and unit-level coverage were in scope.
- **CI/CD**: Continuous integration and deployment pipelines (e.g. GitHub Actions, GitLab CI) for tests, builds, and releases. The project runs locally via Docker Compose and Make.

---
