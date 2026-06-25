"""Pydantic schemas for lists (columns)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.card import CardRead


class ListCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ListUpdate(BaseModel):
    """Partial update (the route applies exclude_unset): send only what changes.
    Both fields optional so you can rename OR set the WIP limit independently.
    `wip_limit: null` clears the limit; `ge=1` rejects nonsensical values."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    wip_limit: Optional[int] = Field(default=None, ge=1, le=999)


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
    wip_limit: Optional[int]  # null = no limit (display-only)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListWithCards(ListRead):
    """A list plus its cards (already ordered by position via the ORM relationship)."""

    cards: list[CardRead] = []
