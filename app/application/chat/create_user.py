from dataclasses import dataclass
from app.domain.chat.repositories.user_repository import UserRepository

@dataclass(frozen=True)
class CreateUserResult:
    user_id: int
    name: str | None

class CreateUserUseCase:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(self, *, name: str) -> CreateUserResult:
        user = self.user_repo.create_user(name=name)
        return CreateUserResult(user_id=user.id, name=user.name)
