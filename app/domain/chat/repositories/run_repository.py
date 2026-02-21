from abc import ABC, abstractmethod
import uuid
from app.domain.chat.entities import Run, RunStatus

class RunRepository(ABC):
    @abstractmethod
    def create_run(self, *, thread_id: uuid.UUID) -> Run: ...

    @abstractmethod
    def get_run(self, *, run_id: uuid.UUID) -> Run | None: ...

    @abstractmethod
    def set_status(self, *, run_id: uuid.UUID, status: RunStatus, error: str | None = None) -> None: ...
