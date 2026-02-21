from __future__ import annotations
from abc import ABC, abstractmethod
import uuid


class RunExecutor(ABC):
    """
    Application-level port for executing a run.

    Implementations may:
    - call a LangGraph graph
    - stream LLM tokens
    - invoke tools via MCP
    - append run events

    Must NOT block the HTTP request thread. Intended to be triggered
    from a background task or worker.
    """

    @abstractmethod
    def start(self, *, thread_id: uuid.UUID, run_id: uuid.UUID) -> None:
        raise NotImplementedError
