from abc import ABC, abstractmethod
import uuid
from app.domain.chat.entities import Thread, Message

class ThreadRepository(ABC):
    @abstractmethod
    def create_thread(self, *, user_id: int) -> Thread: ...

    @abstractmethod
    def get_thread(self, *, thread_id: uuid.UUID) -> Thread | None: ...

    @abstractmethod
    def add_user_message(self, *, thread_id: uuid.UUID, content: str) -> Message: ...

    @abstractmethod
    def add_assistant_message(self, *, thread_id: uuid.UUID, content: str) -> Message: ...

    @abstractmethod
    def list_messages(self, *, thread_id: uuid.UUID) -> list[Message]: ...
