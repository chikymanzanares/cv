import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.thread_repository_sqlalchemy import SqlAlchemyThreadRepository
from app.infrastructure.repositories.run_repository_sqlalchemy import SqlAlchemyRunRepository
from app.infrastructure.repositories.run_event_repository_sqlalchemy import SqlAlchemyRunEventRepository

from app.application.chat.create_thread import CreateThreadUseCase
from app.application.chat.get_thread import GetThreadUseCase
from app.application.chat.post_message_create_run import PostMessageCreateRunUseCase
from app.application.chat.rag_run_executor import RagRunExecutor

router = APIRouter(tags=["threads"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateThreadBody(BaseModel):
    user_id: int


@router.post("/threads")
def create_thread(body: CreateThreadBody, db: Session = Depends(get_db)):
    thread_repo = SqlAlchemyThreadRepository(db)
    uc = CreateThreadUseCase(thread_repo)

    result = uc.execute(user_id=body.user_id)
    return {"thread_id": result.thread_id}


@router.get("/threads/{thread_id}")
def get_thread(thread_id: uuid.UUID, db: Session = Depends(get_db)):
    thread_repo = SqlAlchemyThreadRepository(db)
    uc = GetThreadUseCase(thread_repo)

    try:
        result = uc.execute(thread_id=thread_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "thread_id": result.thread_id,
        "user_id": result.user_id,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in result.messages
        ],
    }


class PostMessageBody(BaseModel):
    content: str


@router.post("/threads/{thread_id}/messages")
def post_message_create_run(
    thread_id: uuid.UUID,
    body: PostMessageBody,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    thread_repo = SqlAlchemyThreadRepository(db)
    run_repo = SqlAlchemyRunRepository(db)

    uc = PostMessageCreateRunUseCase(thread_repo, run_repo)

    try:
        result = uc.execute(thread_id=thread_id, content=body.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    run_id_uuid = uuid.UUID(result.run_id)

    # Capture app.state references before the request context closes.
    rag_service = request.app.state.rag_service
    llm_service = request.app.state.llm_service
    history_turns = request.app.state.history_turns

    # IMPORTANT: background execution must use a NEW db session.
    def run_in_background(run_id: uuid.UUID, thread_id: uuid.UUID):
        bg_db = SessionLocal()
        try:
            bg_run_repo = SqlAlchemyRunRepository(bg_db)
            bg_event_repo = SqlAlchemyRunEventRepository(bg_db)
            bg_thread_repo = SqlAlchemyThreadRepository(bg_db)
            executor = RagRunExecutor(
                run_repo=bg_run_repo,
                event_repo=bg_event_repo,
                thread_repo=bg_thread_repo,
                rag_service=rag_service,
                llm_service=llm_service,
                history_turns=history_turns,
            )
            executor.start(thread_id=thread_id, run_id=run_id)
        finally:
            bg_db.close()

    background.add_task(run_in_background, run_id_uuid, thread_id)

    return {"run_id": result.run_id}
