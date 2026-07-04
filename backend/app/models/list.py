"""List model — a column on a board (e.g. "To Do", "In Progress", "Done")."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.board import Board
    from app.models.card import Card


class List(Base):
    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))

    # FRACTIONAL ORDERING: a float lets us insert a column between two others by
    # averaging their positions — no need to renumber siblings. (See docs for
    # the rebalance fallback when float precision runs out.)
    position: Mapped[float] = mapped_column(Float)

    # Work-in-progress limit: the soft cap on how many cards "should" be in this
    # column. NULL = no limit. It's DISPLAY-ONLY — the UI shows count/limit and
    # flags when over, but the backend never blocks a create/move (so the existing
    # drag flow is unchanged).
    wip_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships ---
    board: Mapped["Board"] = relationship(back_populates="lists")
    cards: Mapped[list["Card"]] = relationship(
        back_populates="list",
        cascade="all, delete-orphan",
        order_by="[Card.position, Card.id]",  # id breaks position ties deterministically
    )
