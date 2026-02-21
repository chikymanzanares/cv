import time
import uuid

from app.application.chat.run_executor import RunExecutor
from app.domain.chat.entities import RunEventType, RunStatus
from app.domain.chat.repositories.run_repository import RunRepository
from app.domain.chat.repositories.run_event_repository import RunEventRepository
from app.domain.chat.repositories.thread_repository import ThreadRepository


class FakeRunExecutor(RunExecutor):
    def __init__(
        self,
        run_repo: RunRepository,
        event_repo: RunEventRepository,
        thread_repo: ThreadRepository,
    ):
        self.run_repo = run_repo
        self.event_repo = event_repo
        self.thread_repo = thread_repo

    def start(self, *, thread_id: uuid.UUID, run_id: uuid.UUID) -> None:
        try:
            self.run_repo.set_status(run_id=run_id, status=RunStatus.running)

            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.tool_start,
                data={"tool": "db.query", "input": {"sql": "SELECT 1"}},
            )
            time.sleep(0.25)

            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.tool_end,
                data={"tool": "db.query", "output": {"rows": [[1]]}},
            )

            text = "Hello 👋. This is a hardcoded run streamed via SSE and stored in Postgres."
            for token in text.split(" "):
                run = self.run_repo.get_run(run_id=run_id)
                if run and run.status == RunStatus.canceled:
                    self.event_repo.append(
                        run_id=run_id,
                        type=RunEventType.canceled,
                        data={"reason": "canceled"},
                    )
                    return

                self.event_repo.append(
                    run_id=run_id,
                    type=RunEventType.token,
                    data={"text": token + " "},
                )
                time.sleep(0.12)

            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.final,
                data={"text": text},
            )

            self.thread_repo.add_assistant_message(thread_id=thread_id, content=text)

            self.run_repo.set_status(run_id=run_id, status=RunStatus.done)

            # Persist the "done" signal as an event too (so SSE replay matches DB)
            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.state,
                data={"status": "done"},
            )

        except Exception as e:
            try:
                self.event_repo.append(
                    run_id=run_id,
                    type=RunEventType.error,
                    data={"error": str(e)},
                )
            finally:
                self.run_repo.set_status(run_id=run_id, status=RunStatus.error, error=str(e))
