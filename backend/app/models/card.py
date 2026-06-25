"""Card model — a task card living inside a list/column."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import card_labels

if TYPE_CHECKING:
    from app.models.label import Label
    from app.models.list import List
    from app.models.user import User


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("lists.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))

    # Optional[str] -> the column is NULLable (a card can have no description).
    # Text (not String) = unbounded length for longer notes.
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Same fractional-ordering idea as List.position, but scoped within a list.
    position: Mapped[float] = mapped_column(Float)

    # --- Jira-style fields. All optional or DEFAULTED so existing rows stay valid. ---
    # assignee: nullable + ON DELETE SET NULL so removing a user doesn't delete cards.
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # server_default (DDL-level) so the column backfills 'medium' on existing rows.
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="medium"
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- G3 Jira fields ---
    # issue_type backfills 'task' on existing rows (same server_default trick).
    issue_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="task"
    )
    # story_points: an optional estimate of effort (Fibonacci-ish in practice).
    story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # onupdate=func.now() -> the DB refreshes this every time the row changes.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    list: Mapped["List"] = relationship(back_populates="cards")
    assignee: Mapped[Optional["User"]] = relationship("User")  # uses assignee_id
    # Non-annotated relationship (no `Mapped[list[...]]`): with a cross-module
    # string ref under `secondary=`, SQLAlchemy can't reliably read the annotation
    # to detect the collection. Omitting it lets a `secondary` M2M default to a
    # list, which is what we want. (`card.labels` is still a list at runtime.)
    labels = relationship("Label", secondary=card_labels, back_populates="cards")
