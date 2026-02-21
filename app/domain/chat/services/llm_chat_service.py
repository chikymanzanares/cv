from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMChatService(ABC):
    """
    Port for streaming chat completion.

    Implementations provide a stream() method that yields text tokens one by one.
    The system parameter carries the RAG context and persona instructions.
    The messages list follows the OpenAI-style role/content format.
    """

    @abstractmethod
    def stream(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """Yield text tokens incrementally as they arrive from the LLM."""
        raise NotImplementedError
