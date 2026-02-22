# AGENTS.md

## Purpose

This document defines how **execution agents** (LLM-driven or task
executors) must interact with the system.

The backend implements a **Run-based execution model** with:

-   Persistent Threads
-   Runs as execution units
-   RunEvents as append-only execution logs
-   SSE-based streaming
-   Cancelable execution

This contract ensures agents remain:

-   Stateless
-   Resumable
-   Observable
-   Multi-pod safe

------------------------------------------------------------------------

## Core Concepts

### Thread

Represents a long-lived conversation context.

Agents **must not** mutate Thread state directly. All execution happens
within a Run.

------------------------------------------------------------------------

### Run

A Run represents a single execution lifecycle triggered by:

POST /api/threads/{thread_id}/messages

Each Run has:

-   status
    -   queued
    -   running
    -   done
    -   error
    -   canceled
-   timestamps
-   append-only RunEvents

Runs are the only execution boundary for agents.

Agents MUST:

-   Set status to `running` when execution starts
-   Set status to `done`, `error`, or `canceled` when finished

------------------------------------------------------------------------

### RunEvents

RunEvents are the execution log.

They are:

-   ordered
-   append-only
-   persisted
-   streamable via SSE

Types:

-   token
-   tool_start
-   tool_end
-   final
-   error
-   canceled
-   state
-   heartbeat

Agents must communicate execution state **only** via RunEvents.

Example:

tool_start -\> token\* -\> final -\> state(done)

------------------------------------------------------------------------

## Streaming Model

Clients consume execution via:

GET /api/runs/{run_id}/events

Uses:

Server-Sent Events (SSE)

Supports:

Last-Event-ID

This allows:

-   reconnect
-   resume
-   multi-pod execution
-   crash recovery

Agents MUST ensure:

-   All execution steps are persisted via RunEvents
-   Execution can be resumed from any seq

### SSE event payloads

Each SSE message has an `event` type and a JSON `data` payload. The stream sends `id: <seq>` so clients can use the `Last-Event-ID` header for resume.

| event | data shape |
|-------|------------|
| token | `{ "text": "..." }` — incremental assistant text |
| tool_start | `{ "tool": "...", "input": { ... } }` |
| tool_end | `{ "tool": "...", "output": { ... } }` |
| final | `{ "text": "...", "sources": ["cv_001", ...] }` — full response and CV IDs used |
| state | `{ "status": "done" \| "error" \| "canceled" }` |
| error | `{ "error": "..." }` |
| canceled | `{ "reason": "..." }` |
| heartbeat | sent as a comment line (e.g. `: ping`); no data payload |

Source of truth: [app/infrastructure/web/routers/runs.py](app/infrastructure/web/routers/runs.py), [app/domain/chat/entities.py](app/domain/chat/entities.py) (RunEventType).

------------------------------------------------------------------------

## Cancellation Contract

Clients may cancel a Run:

POST /api/runs/{run_id}/cancel

Agents must:

1.  Periodically check Run status
2.  If status == canceled:
    -   append RunEvent(type=canceled)
    -   stop execution immediately
    -   do not append final
    -   do not set done

------------------------------------------------------------------------

## Execution Rules

Agents MUST:

-   Treat RunEvents as the source of truth
-   Never assume in-memory execution continuity
-   Poll run status during long execution
-   Emit tokens incrementally when possible
-   Emit final output before marking done
-   Emit state event when finishing

------------------------------------------------------------------------

## Persistence Guarantees

All agent output must be written via:

RunEventRepository.append()

Never stream directly from memory.

SSE clients rely on persisted events to:

-   reconnect
-   resume after network loss
-   survive pod restarts

------------------------------------------------------------------------

## Multi-Pod Safety

SSE connections are:

-   pod-affine
-   ephemeral

RunEvents are:

-   stored in Postgres
-   globally accessible

Execution must therefore be:

short-lived stateless replayable

------------------------------------------------------------------------

## Infrastructure Constraints

-   Postgres is the execution log store
-   Alembic handles schema migrations
-   Docker Compose handles startup
-   migrate service applies migrations automatically

------------------------------------------------------------------------

## Testing Expectations

Agents should be verifiable via:

-   POST /api/threads
-   POST /api/threads/{thread_id}/messages
-   GET /api/runs/{run_id}
-   GET /api/runs/{run_id}/events
-   POST /api/runs/{run_id}/cancel

RunEvents must reflect execution lifecycle deterministically.

------------------------------------------------------------------------

## Future Integrations

This execution contract is designed to support:

-   LangGraph
-   Celery
-   Background workers
-   Distributed executors

without changing client streaming behavior.
