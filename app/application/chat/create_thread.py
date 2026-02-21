from dataclasses import dataclass

from app.domain.chat.repositories.thread_repository import ThreadRepository


@dataclass(frozen=True)
class CreateThreadResult:
    thread_id: str


class CreateThreadUseCase:
    def __init__(self, thread_repo: ThreadRepository):
        self.thread_repo = thread_repo

    def execute(self, *, user_id: int) -> CreateThreadResult:
        thread = self.thread_repo.create_thread(user_id=user_id)
        return CreateThreadResult(thread_id=str(thread.id))
