from dataclasses import dataclass
import uuid

from app.domain.chat.repositories.thread_repository import ThreadRepository


@dataclass(frozen=True)
class ThreadMessageDTO:
    id: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class GetThreadResult:
    thread_id: str
    user_id: int
    messages: list[ThreadMessageDTO]


class GetThreadUseCase:
    def __init__(self, thread_repo: ThreadRepository):
        self.thread_repo = thread_repo

    def execute(self, *, thread_id: uuid.UUID) -> GetThreadResult:
        thread = self.thread_repo.get_thread(thread_id=thread_id)
        if not thread:
            raise ValueError("Thread not found")

        messages = self.thread_repo.list_messages(thread_id=thread_id)

        return GetThreadResult(
            thread_id=str(thread.id),
            user_id=thread.user_id,
            messages=[
                ThreadMessageDTO(
                    id=str(m.id),
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at.isoformat(),
                )
                for m in messages
            ],
        )
