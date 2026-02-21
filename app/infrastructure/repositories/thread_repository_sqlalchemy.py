import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.chat.entities import Thread as DomainThread, Message as DomainMessage
from app.domain.chat.repositories.thread_repository import ThreadRepository

from app.infrastructure.models.thread import Thread
from app.infrastructure.models.message import Message


class SqlAlchemyThreadRepository(ThreadRepository):
    def __init__(self, db: Session):
        self.db = db

    def create_thread(self, *, user_id: int) -> DomainThread:
        th = Thread(user_id=user_id)
        self.db.add(th)
        self.db.commit()
        self.db.refresh(th)
        return DomainThread(id=th.id, user_id=th.user_id, created_at=th.created_at)

    def get_thread(self, *, thread_id: uuid.UUID) -> DomainThread | None:
        th = self.db.get(Thread, thread_id)
        if not th:
            return None
        return DomainThread(id=th.id, user_id=th.user_id, created_at=th.created_at)

    def add_user_message(self, *, thread_id: uuid.UUID, content: str) -> DomainMessage:
        m = Message(thread_id=thread_id, role="user", content=content)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return DomainMessage(
            id=m.id, thread_id=m.thread_id, role=m.role, content=m.content, created_at=m.created_at
        )

    def add_assistant_message(self, *, thread_id: uuid.UUID, content: str) -> DomainMessage:
        m = Message(thread_id=thread_id, role="assistant", content=content)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return DomainMessage(
            id=m.id, thread_id=m.thread_id, role=m.role, content=m.content, created_at=m.created_at
        )

    def list_messages(self, *, thread_id: uuid.UUID) -> list[DomainMessage]:
        rows = self.db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc())
        ).scalars().all()

        return [
            DomainMessage(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in rows
        ]
