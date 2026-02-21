from abc import ABC, abstractmethod
import uuid
from app.domain.chat.entities import RunEvent, RunEventType

class RunEventRepository(ABC):
    @abstractmethod
    def append(self, *, run_id: uuid.UUID, type: RunEventType, data: dict) -> RunEvent: ...

    @abstractmethod
    def list_after(self, *, run_id: uuid.UUID, after_seq: int) -> list[RunEvent]: ...
