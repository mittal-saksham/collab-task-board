"""Activity model — an append-only record of something that happened on a board.

This is the board's audit/feed: "Alice created card X", "Bob moved Y", "Carol
commented on Z". Rows are written as a side-effect of other routes (via
`app/services/activity_log.py`) and only ever read back as a feed — never edited.

Design choices that keep history durable:
- `actor_id` is `ON DELETE SET NULL` — removing a user keeps the history line.
- `card_id` is nullable + `ON DELETE SET NULL` — some events (member added) have
  no card, and deleting a card must not erase the record that it once existed.
  The human-readable `summary` already captured the card's title at the time.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    card_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    # A short machine code for the event type, e.g. "created_card", "commented".
    verb: Mapped[str] = mapped_column(String(40))
    # The pre-rendered human-readable line, e.g. 'moved "Wire up drag" to Doing'.
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    actor: Mapped[Optional["User"]] = relationship("User")
