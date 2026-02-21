from dataclasses import dataclass
import uuid

from app.domain.chat.repositories.run_repository import RunRepository


@dataclass(frozen=True)
class GetRunResult:
    run_id: str
    thread_id: str
    status: str
    created_at: str | None
    started_at: str | None
    finished_at: str | None
    error: str | None


class GetRunUseCase:
    def __init__(self, run_repo: RunRepository):
        self.run_repo = run_repo

    def execute(self, *, run_id: uuid.UUID) -> GetRunResult:
        run = self.run_repo.get_run(run_id=run_id)
        if not run:
            raise ValueError("Run not found")

        return GetRunResult(
            run_id=str(run.id),
            thread_id=str(run.thread_id),
            status=run.status.value,
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.started_at.isoformat() if run.started_at else None,
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            error=run.error,
        )
