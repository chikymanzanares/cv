import uuid
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.domain.chat.entities import RunEvent as DomainRunEvent, RunEventType
from app.domain.chat.repositories.run_event_repository import RunEventRepository

from app.infrastructure.models.run_event import RunEvent


class SqlAlchemyRunEventRepository(RunEventRepository):
    def __init__(self, db: Session):
        self.db = db

    def append(self, *, run_id: uuid.UUID, type: RunEventType, data: dict) -> DomainRunEvent:
        # Next seq per run_id (simple approach; OK for technical test)
        last = self.db.execute(
            select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id)
        ).scalar_one()
        seq = int(last or 0) + 1

        ev = RunEvent(run_id=run_id, seq=seq, type=type, data=data)
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)

        return DomainRunEvent(
            id=ev.id,
            run_id=ev.run_id,
            seq=ev.seq,
            type=ev.type,
            data=ev.data,
            created_at=ev.created_at,
        )

    def list_after(self, *, run_id: uuid.UUID, after_seq: int) -> list[DomainRunEvent]:
        rows = self.db.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
            .order_by(RunEvent.seq.asc())
        ).scalars().all()

        return [
            DomainRunEvent(
                id=e.id,
                run_id=e.run_id,
                seq=e.seq,
                type=e.type,
                data=e.data,
                created_at=e.created_at,
            )
            for e in rows
        ]
