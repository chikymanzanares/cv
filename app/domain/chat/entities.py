from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"
    canceled = "canceled"


class RunEventType(str, Enum):
    token = "token"
    tool_start = "tool_start"
    tool_end = "tool_end"
    state = "state"
    final = "final"
    error = "error"
    canceled = "canceled"
    heartbeat = "heartbeat"


@dataclass(frozen=True)
class Thread:
    id: uuid.UUID
    user_id: int
    created_at: datetime


@dataclass(frozen=True)
class Message:
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class Run:
    id: uuid.UUID
    thread_id: uuid.UUID
    status: RunStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


@dataclass(frozen=True)
class RunEvent:
    id: uuid.UUID
    run_id: uuid.UUID
    seq: int
    type: RunEventType
    data: dict
    created_at: datetime

@dataclass(frozen=True)
class User:
    id: int
    name: str | None