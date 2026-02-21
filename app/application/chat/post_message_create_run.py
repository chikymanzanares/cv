from dataclasses import dataclass
import uuid

from app.domain.chat.repositories.thread_repository import ThreadRepository
from app.domain.chat.repositories.run_repository import RunRepository


@dataclass(frozen=True)
class PostMessageCreateRunResult:
    run_id: str


class PostMessageCreateRunUseCase:
    """
    Fast path:
    - validate thread exists
    - store user message (persist in database)
    - create a queued run (status="queued")
    - return run_id (frontend will use GET /api/runs/{run_id}/events (SSE))

    Run execution (fake/langgraph) is started outside this use case (e.g., FastAPI BackgroundTasks),
    so the HTTP request stays fast.
    """

    def __init__(self, thread_repo: ThreadRepository, run_repo: RunRepository):
        self.thread_repo = thread_repo
        self.run_repo = run_repo

    def execute(self, *, thread_id: uuid.UUID, content: str) -> PostMessageCreateRunResult:
        thread = self.thread_repo.get_thread(thread_id=thread_id)
        if not thread:
            raise ValueError("Thread not found")

        self.thread_repo.add_user_message(thread_id=thread_id, content=content)
        run = self.run_repo.create_run(thread_id=thread_id)

        return PostMessageCreateRunResult(run_id=str(run.id))
