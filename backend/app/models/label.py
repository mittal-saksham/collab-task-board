"""Label model — a colored, board-scoped tag that can be attached to cards.

Cards ↔ Labels is many-to-many via the `card_labels` association table.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import card_labels

if TYPE_CHECKING:
    from app.models.card import Card


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    # A simple color name (the frontend maps it to a Tailwind class).
    color: Mapped[str] = mapped_column(String(20), nullable=False, server_default="slate")

    # Cards carrying this label (non-annotated — see Card.labels for why).
    cards = relationship("Card", secondary=card_labels, back_populates="labels")
