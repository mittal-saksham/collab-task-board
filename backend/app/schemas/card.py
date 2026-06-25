"""Pydantic schemas for cards."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.label import LabelRead
from app.schemas.user import UserBrief

# The five Jira priority levels.
Priority = Literal["highest", "high", "medium", "low", "lowest"]


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class CardUpdate(BaseModel):
    """All fields optional. The route applies only the fields actually SENT
    (`exclude_unset`), so `assignee_id: null` unassigns while omitting it leaves
    the assignee unchanged."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    assignee_id: Optional[int] = None


class CardMove(BaseModel):
    list_id: int
    after_id: Optional[int] = None


class CardRead(BaseModel):
    id: int
    list_id: int
    title: str
    description: Optional[str]
    position: float
    priority: str
    due_date: Optional[date]
    assignee: Optional[UserBrief]  # built from card.assignee (a User) or null
    labels: list[LabelRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
