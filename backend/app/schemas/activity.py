"""Pydantic schemas for the activity feed (read-only)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserBrief


class ActivityRead(BaseModel):
    id: int
    board_id: int
    actor: Optional[UserBrief]  # null if the user was later removed (SET NULL)
    card_id: Optional[int]
    verb: str
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
