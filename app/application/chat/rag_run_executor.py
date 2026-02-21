from __future__ import annotations

import logging
import uuid

from app.application.chat.run_executor import RunExecutor

logger = logging.getLogger(__name__)
from app.domain.chat.entities import RunEventType, RunStatus
from app.domain.chat.repositories.run_repository import RunRepository
from app.domain.chat.repositories.run_event_repository import RunEventRepository
from app.domain.chat.repositories.thread_repository import ThreadRepository
from app.domain.chat.services.llm_chat_service import LLMChatService
from app.infrastructure.rag.rag_chat_service import RagChatService

_SYSTEM_PROMPT = """\
You are an expert CV screening assistant.
Your job is to help users find and evaluate candidates from a collection of CVs.

Rules:
- Answer based ONLY on the CV excerpts provided in this message.
- If the answer cannot be found in the provided CVs, say so clearly.
- When referring to a candidate, always mention their name (if available) and their CV ID (e.g. cv_029).
- Be concise, accurate, and structured. Use bullet points when listing multiple candidates.
"""


def _build_system(chunks: list[dict]) -> str:
    """Combine the base system prompt with the RAG context block."""
    if not chunks:
        context = "No relevant CV excerpts were found for this query."
    else:
        lines = ["## Relevant CV excerpts\n"]
        for chunk in chunks:
            lines.append(f"[{chunk['cv_id']}]")
            lines.append(chunk["text"].strip())
            lines.append("")
        context = "\n".join(lines)
    return f"{_SYSTEM_PROMPT}\n{context}"


def _build_llm_messages(history: list, current_query: str) -> list[dict]:
    """Build the messages list: recent history turns + current user query."""
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": current_query})
    return messages


class RagRunExecutor(RunExecutor):
    """
    Real run executor: retrieves relevant CV chunks via RAG, then streams
    an LLM response token by token as RunEvents.

    Lifecycle mirrors FakeRunExecutor:
      tool_start → tool_end → token* → final → state(done)
    """

    def __init__(
        self,
        run_repo: RunRepository,
        event_repo: RunEventRepository,
        thread_repo: ThreadRepository,
        rag_service: RagChatService,
        llm_service: LLMChatService,
        history_turns: int = 6,
    ):
        self.run_repo = run_repo
        self.event_repo = event_repo
        self.thread_repo = thread_repo
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.history_turns = history_turns

    def start(self, *, thread_id: uuid.UUID, run_id: uuid.UUID) -> None:
        try:
            self.run_repo.set_status(run_id=run_id, status=RunStatus.running)

            # --- 1. Read conversation history ---
            all_messages = self.thread_repo.list_messages(thread_id=thread_id)
            if not all_messages:
                raise ValueError("Thread has no messages.")

            current_query = all_messages[-1].content
            recent_history = all_messages[:-1][-(self.history_turns):]

            logger.info(
                "[run:%s] START | thread=%s | query=%r | history=%d msgs",
                run_id, thread_id, current_query[:120], len(recent_history),
            )

            # --- 2. RAG retrieval ---
            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.tool_start,
                data={"tool": "rag.search", "input": {"query": current_query}},
            )

            search_result = self.rag_service.search(current_query)
            chunks = search_result["results"]

            # Deduplicate cv_ids preserving relevance order
            seen: set[str] = set()
            sources: list[str] = []
            for chunk in chunks:
                cv_id = chunk["cv_id"]
                if cv_id not in seen:
                    seen.add(cv_id)
                    sources.append(cv_id)

            logger.info(
                "[run:%s] RAG done | chunks=%d | sources=%s",
                run_id, len(chunks), sources,
            )

            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.tool_end,
                data={"tool": "rag.search", "output": {"sources": sources, "chunks": len(chunks)}},
            )

            # --- 3. Build prompt ---
            system = _build_system(chunks)
            messages = _build_llm_messages(recent_history, current_query)

            # --- 4. Stream LLM response ---
            logger.info("[run:%s] LLM streaming start", run_id)
            full_text = ""
            token_count = 0
            for token in self.llm_service.stream(system=system, messages=messages):
                run = self.run_repo.get_run(run_id=run_id)
                if run and run.status == RunStatus.canceled:
                    logger.info("[run:%s] CANCELED by client after %d tokens", run_id, token_count)
                    self.event_repo.append(
                        run_id=run_id,
                        type=RunEventType.canceled,
                        data={"reason": "canceled"},
                    )
                    return

                self.event_repo.append(
                    run_id=run_id,
                    type=RunEventType.token,
                    data={"text": token},
                )
                full_text += token
                token_count += 1

            logger.info(
                "[run:%s] LLM streaming done | tokens=%d | chars=%d",
                run_id, token_count, len(full_text),
            )

            # --- 5. Persist final response with source indication ---
            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.final,
                data={"text": full_text, "sources": sources},
            )

            self.thread_repo.add_assistant_message(thread_id=thread_id, content=full_text)

            self.run_repo.set_status(run_id=run_id, status=RunStatus.done)
            self.event_repo.append(
                run_id=run_id,
                type=RunEventType.state,
                data={"status": "done"},
            )

            logger.info("[run:%s] DONE", run_id)

        except Exception as e:
            logger.exception("[run:%s] ERROR: %s", run_id, e)
            try:
                self.event_repo.append(
                    run_id=run_id,
                    type=RunEventType.error,
                    data={"error": str(e)},
                )
            finally:
                self.run_repo.set_status(run_id=run_id, status=RunStatus.error, error=str(e))
