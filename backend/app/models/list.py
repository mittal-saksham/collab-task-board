"""List model — a column on a board (e.g. "To Do", "In Progress", "Done")."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, func
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Relationships ---
    board: Mapped["Board"] = relationship(back_populates="lists")
    cards: Mapped[list["Card"]] = relationship(
        back_populates="list",
        cascade="all, delete-orphan",
        order_by="Card.position",
    )
