"""Pydantic schemas for lists (columns)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.card import CardRead


class ListCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ListUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ListMove(BaseModel):
    """Reorder a list within its board. Server computes the new position."""

    # Place this list immediately AFTER the list with this id.
    # None -> move to the FRONT of the board.
    after_id: Optional[int] = None


class ListRead(BaseModel):
    id: int
    board_id: int
    title: str
    position: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListWithCards(ListRead):
    """A list plus its cards (already ordered by position via the ORM relationship)."""

    cards: list[CardRead] = []
