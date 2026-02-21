class AppError(Exception):
    """Base class for application-level errors."""


class ConflictError(AppError):
    """Raised when a resource already exists (HTTP 409)."""


class UserAlreadyExistsError(AppError):
    """Raised when a user already exists (HTTP 401)."""
    def __init__(self, message: str, user_id: int, name: str | None):
        super().__init__(message)
        self.user_id = user_id
        self.name = name
