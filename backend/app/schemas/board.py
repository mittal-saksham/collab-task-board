"""Pydantic schemas for boards."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.list import ListWithCards


class BoardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class BoardUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class BoardRead(BaseModel):
    """A board's own fields (used in lists of boards and after create/update)."""

    id: int
    title: str
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoardDetail(BoardRead):
    """A board PLUS its full contents — what GET /boards/{id} returns.

    `lists` is loaded from the ORM relationship (ordered by position), and each
    list carries its ordered `cards`. This is the single payload the frontend
    needs to render an entire board.
    """

    lists: list[ListWithCards] = []


class BoardSummary(BaseModel):
    """Response for the optional 'summarize board' endpoint."""

    summary: str
