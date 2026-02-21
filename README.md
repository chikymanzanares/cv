
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
   - **Google (Gemini):** set `LLM_PROVIDER` to the value used for Gemini and add:
     ```
     GEMINI_API_KEY=your-google-api-key-here
     ```

Without a valid `.env` and the corresponding API key, the project will not work.

---

## Start the project

1. **Generate CV data and PDFs** (required before first run). One command does both:

   ```
   make -C cv_generation gen-all
   ```

   Or step by step: `make -C cv_generation gen-data` then `make -C cv_generation gen-pdf`.

2. **Run everything** (API + Postgres + migrations):

   ```
   make up
   ```

This will:
- Build the API image
- Start Postgres
- Run Alembic migrations
- Start FastAPI on http://localhost:8000

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

## Next Steps

Before integrating an async execution engine (LangGraph / Celery), we recommend:

- Adding application-layer tests for:
  - CreateUser
  - CreateThread
  - PostMessageCreateRun
  - CancelRun
  - SSE replay with Last-Event-ID

---
