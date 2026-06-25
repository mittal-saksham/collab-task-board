"""Board model — a single project board owned by one user."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.list import List
    from app.models.membership import Membership
    from app.models.user import User


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))

    # ForeignKey ties each board to its owner row in `users`.
    # ondelete="CASCADE" -> if the owner is deleted, the DB removes their boards.
    # owner_id is our AUTHORITY for "who owns this board" (used in auth checks).
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships ---
    owner: Mapped["User"] = relationship(back_populates="owned_boards")

    # All membership rows for this board (includes the owner's own membership,
    # which we create alongside the board so "boards I can access" is one query).
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="board", cascade="all, delete-orphan"
    )

    # Columns on the board, kept ordered by their float position when loaded.
    lists: Mapped[list["List"]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
        order_by="List.position",
    )
