import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.domain.chat.entities import Run as DomainRun, RunStatus
from app.domain.chat.repositories.run_repository import RunRepository

from app.infrastructure.models.run import Run


class SqlAlchemyRunRepository(RunRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, *, thread_id: uuid.UUID) -> DomainRun:
        r = Run(thread_id=thread_id, status=RunStatus.queued)
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        return DomainRun(
            id=r.id,
            thread_id=r.thread_id,
            status=r.status,
            created_at=r.created_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            error=r.error,
        )

    def get_run(self, *, run_id: uuid.UUID) -> DomainRun | None:
        r = self.db.get(Run, run_id)
        if not r:
            return None
        return DomainRun(
            id=r.id,
            thread_id=r.thread_id,
            status=r.status,
            created_at=r.created_at,
            started_at=r.started_at,
            finished_at=r.finished_at,
            error=r.error,
        )

    def set_status(self, *, run_id: uuid.UUID, status: RunStatus, error: str | None = None) -> None:
        r = self.db.get(Run, run_id)
        if not r:
            return

        r.status = status

        if status == RunStatus.running and r.started_at is None:
            r.started_at = datetime.now(timezone.utc)

        if status in (RunStatus.done, RunStatus.error, RunStatus.canceled):
            r.finished_at = datetime.now(timezone.utc)

        if error is not None:
            r.error = error

        self.db.commit()
