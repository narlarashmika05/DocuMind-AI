from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.clock import utcnow


class Base(DeclarativeBase):
    """Parent class of every ORM model. Alembic reads Base.metadata to generate migrations."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
