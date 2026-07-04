"""Pydantic schemas for cards."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.label import LabelRead
from app.schemas.user import UserBrief

# The five Jira priority levels.
Priority = Literal["highest", "high", "medium", "low", "lowest"]
# Issue types (G3).
IssueType = Literal["task", "bug", "story"]


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
    issue_type: Optional[IssueType] = None
    # ge=0 → no negative estimates. Present as null clears it (exclude_unset).
    story_points: Optional[int] = Field(default=None, ge=0, le=999)

    # These columns are NOT NULL in the database, so "clear it" makes no sense —
    # an explicit `"title": null` would otherwise slip through Optional and blow
    # up as a 500 at commit time. Validators don't run on defaults, so an ABSENT
    # field (= "leave unchanged") is still fine.
    @field_validator("title", "priority", "issue_type")
    @classmethod
    def reject_explicit_null(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return v


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
    issue_type: str
    story_points: Optional[int]
    assignee: Optional[UserBrief]  # built from card.assignee (a User) or null
    labels: list[LabelRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
