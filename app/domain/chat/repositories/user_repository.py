from abc import ABC, abstractmethod
from app.domain.chat.entities import User


class UserRepository(ABC):
    @abstractmethod
    def create_user(self, *, name: str) -> User: ...

    @abstractmethod
    def get_user_by_name(self, *, name: str) -> User | None: ...
