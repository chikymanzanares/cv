from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.errors import UserAlreadyExistsError
from app.domain.chat.entities import User as DomainUser
from app.domain.chat.repositories.user_repository import UserRepository
from app.infrastructure.models.user import User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_name(self, *, name: str) -> DomainUser | None:
        row = self.db.execute(select(User).where(User.name == name)).scalar_one_or_none()
        if row is None:
            return None
        return DomainUser(id=row.id, name=row.name)

    def create_user(self, *, name: str) -> DomainUser:
        u = User(name=name)
        self.db.add(u)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # Fallback if another request created the user between our check and insert
            existing = self.get_user_by_name(name=name)
            if existing:
                raise UserAlreadyExistsError(
                    message=f"User with name '{name}' already exists",
                    user_id=existing.id,
                    name=existing.name,
                )
            raise
        self.db.refresh(u)
        return DomainUser(id=u.id, name=u.name)
