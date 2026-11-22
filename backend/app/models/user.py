from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.refresh_token import RefreshToken


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(default=True)

    # passive_deletes: let MySQL's ON DELETE CASCADE remove children instead of loading them first
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
