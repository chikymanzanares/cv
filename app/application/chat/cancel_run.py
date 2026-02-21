from dataclasses import dataclass
import uuid

from app.domain.chat.entities import RunStatus
from app.domain.chat.repositories.run_repository import RunRepository


@dataclass(frozen=True)
class CancelRunResult:
    status: str


class CancelRunUseCase:
    def __init__(self, run_repo: RunRepository):
        self.run_repo = run_repo

    def execute(self, *, run_id: uuid.UUID) -> CancelRunResult:
        run = self.run_repo.get_run(run_id=run_id)
        if not run:
            raise ValueError("Run not found")

        # Idempotent cancel
        if run.status in (RunStatus.done, RunStatus.error, RunStatus.canceled):
            return CancelRunResult(status=run.status.value)

        self.run_repo.set_status(run_id=run_id, status=RunStatus.canceled)
        return CancelRunResult(status=RunStatus.canceled.value)
