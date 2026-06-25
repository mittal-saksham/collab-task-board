"""Pydantic schemas for cards."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class CardUpdate(BaseModel):
    # All optional: a PATCH can change just the title, just the description, etc.
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class CardMove(BaseModel):
    """Where to move a card. The server computes the new float position."""

    # The list to move into (may equal the current list for a pure reorder).
    list_id: int
    # Place this card immediately AFTER the card with this id.
    # None  -> move to the FRONT of the target list.
    after_id: Optional[int] = None


class CardRead(BaseModel):
    id: int
    list_id: int
    title: str
    description: Optional[str]
    position: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
