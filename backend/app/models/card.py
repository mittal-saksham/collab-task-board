"""Card model — a task card living inside a list/column."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.list import List


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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # onupdate=func.now() -> the DB refreshes this every time the row changes.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    list: Mapped["List"] = relationship(back_populates="cards")
