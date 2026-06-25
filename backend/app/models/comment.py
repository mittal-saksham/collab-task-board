"""Comment model — a message a user posts on a card.

Comments are the card-level discussion thread. Each belongs to one card and one
author. Deleting the card (or the author) removes their comments via CASCADE.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Text (not String) = unbounded length, for longer comments.
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Scalar FK relationship → keep the Mapped annotation (only `secondary` M2M
    # collections drop it; see Card.labels for the why).
    author: Mapped["User"] = relationship("User")
