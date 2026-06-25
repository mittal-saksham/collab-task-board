"""User model — a person who can log in and own/join boards."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Imported ONLY for type checkers (not at runtime) to avoid circular imports.
# The relationships below reference these classes by *string name*, which
# SQLAlchemy resolves later from its registry — so no real import is needed.
if TYPE_CHECKING:
    from app.models.board import Board
    from app.models.membership import Membership


class User(Base):
    __tablename__ = "users"

    # `Mapped[int]` + `mapped_column(...)` is SQLAlchemy 2.0 style. The Python
    # type annotation (int, str, datetime) drives the column type.
    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True -> no two users share an email. index=True -> fast lookups by
    # email (which we do on every login).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # We NEVER store the raw password — only its bcrypt hash. See core/security.py.
    hashed_password: Mapped[str] = mapped_column(String(255))

    # server_default=func.now() -> the DATABASE fills this in (SQL NOW()), so the
    # timestamp is consistent regardless of the app server's clock.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships (Python-side convenience, not extra DB columns) ---
    # back_populates wires the two sides together so they stay in sync in memory.
    # cascade="all, delete-orphan" -> deleting a user deletes their owned boards
    # and memberships too.
    owned_boards: Mapped[list["Board"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
