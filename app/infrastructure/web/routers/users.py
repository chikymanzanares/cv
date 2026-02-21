from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.user_repository_sqlalchemy import SqlAlchemyUserRepository

from app.application.chat.create_user import CreateUserUseCase
from app.application.errors import UserAlreadyExistsError


router = APIRouter(tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateUserBody(BaseModel):
    name: str


@router.post("/users")
def create_user(body: CreateUserBody, db: Session = Depends(get_db)):
    user_repo = SqlAlchemyUserRepository(db)
    uc = CreateUserUseCase(user_repo)

    try:
        result = uc.execute(name=body.name)
        return {"user_id": result.user_id, "name": result.name}
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=401,
            detail={
                "message": e.args[0],
                "user_id": e.user_id,
                "name": e.name
            }
        )
