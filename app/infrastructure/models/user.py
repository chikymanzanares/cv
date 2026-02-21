from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), unique=True, index=True, nullable=True)

    threads: Mapped[list["Thread"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
