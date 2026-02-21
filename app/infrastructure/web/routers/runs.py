import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.run_repository_sqlalchemy import SqlAlchemyRunRepository
from app.infrastructure.repositories.run_event_repository_sqlalchemy import SqlAlchemyRunEventRepository

from app.application.chat.get_run import GetRunUseCase
from app.application.chat.cancel_run import CancelRunUseCase


router = APIRouter(tags=["runs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sse_frame(*, data: dict, event: str | None = None, event_id: int | None = None) -> str:
    import json
    msg = ""
    if event_id is not None:
        msg += f"id: {event_id}\n"
    if event is not None:
        msg += f"event: {event}\n"
    msg += "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"
    return msg


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run_repo = SqlAlchemyRunRepository(db)
    uc = GetRunUseCase(run_repo)

    try:
        result = uc.execute(run_id=run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "run_id": result.run_id,
        "thread_id": result.thread_id,
        "status": result.status,
        "created_at": result.created_at,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "error": result.error,
    }


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run_repo = SqlAlchemyRunRepository(db)
    uc = CancelRunUseCase(run_repo)

    try:
        result = uc.execute(run_id=run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"ok": True, "status": result.status}


@router.get("/runs/{run_id}/events")
def stream_run_events(run_id: uuid.UUID, request: Request):
    last_event_id = request.headers.get("Last-Event-ID")
    after_seq = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

    async def gen():
        nonlocal after_seq
        yield ": connected\n\n"

        poll_every = 0.35
        heartbeat_every = 15.0
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            if await request.is_disconnected():
                return

            # short-lived db session per poll
            db = SessionLocal()
            try:
                run_repo = SqlAlchemyRunRepository(db)
                event_repo = SqlAlchemyRunEventRepository(db)

                run = run_repo.get_run(run_id=run_id)
                if not run:
                    yield sse_frame(event="error", event_id=after_seq + 1, data={"error": "Run not found"})
                    return

                events = event_repo.list_after(run_id=run_id, after_seq=after_seq)
                for ev in events:
                    after_seq = ev.seq
                    yield sse_frame(event=ev.type.value, event_id=ev.seq, data=ev.data)

                if run.status.value in ("done", "error", "canceled"):
                    yield sse_frame(event="done", event_id=after_seq + 1, data={"status": run.status.value})
                    return

            finally:
                db.close()

            now = asyncio.get_event_loop().time()
            if now - last_heartbeat >= heartbeat_every:
                last_heartbeat = now
                yield ": ping\n\n"

            await asyncio.sleep(poll_every)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
