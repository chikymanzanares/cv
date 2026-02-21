import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class RunEventType(str, Enum):
    token = "token"
    tool_start = "tool_start"
    tool_end = "tool_end"
    state = "state"
    final = "final"
    error = "error"
    canceled = "canceled"
    heartbeat = "heartbeat"  # opcional


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # seq es CLAVE para SSE: lo mandas como "id:" y permite Last-Event-ID
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    type: Mapped[RunEventType] = mapped_column(
        SAEnum(RunEventType, name="run_event_type"),
        nullable=False,
        index=True,
    )

    data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    run: Mapped["Run"] = relationship(back_populates="events")

    __table_args__ = (
        # no pueden repetirse seq dentro de un run
        UniqueConstraint("run_id", "seq", name="uq_run_events_run_id_seq"),
        # para leer "tail" rápido: SELECT ... WHERE run_id=? AND seq>? ORDER BY seq
        Index("ix_run_events_run_id_seq", "run_id", "seq"),
    )
