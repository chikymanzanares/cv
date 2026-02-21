from __future__ import annotations
from abc import ABC, abstractmethod
import uuid

class RunExecutor(ABC):
    @abstractmethod
    def start(self, *, thread_id: uuid.UUID, run_id: uuid.UUID) -> None:
        raise NotImplementedError
