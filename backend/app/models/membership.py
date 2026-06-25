"""Membership model — the join table making boards multi-user.

This is a classic many-to-many "association" table: a User can belong to many
Boards, and a Board can have many Users. Each row is one (user, board) pair,
plus a `role` so we can extend to richer permissions later.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.board import Board
    from app.models.user import User


class Membership(Base):
    __tablename__ = "memberships"

    # A user can only be a member of a given board ONCE. This DB-level constraint
    # stops duplicate invites from creating duplicate rows.
    __table_args__ = (
        UniqueConstraint("board_id", "user_id", name="uq_membership_board_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # "owner" or "member" for now. Defaulting to "member" means we can add
    # "editor"/"viewer" later without a schema change. NOTE: authorization still
    # treats Board.owner_id as the single source of truth for ownership.
    role: Mapped[str] = mapped_column(String(20), default="member")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships ---
    board: Mapped["Board"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
