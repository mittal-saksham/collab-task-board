"""Pydantic schemas for comments."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserBrief


class CommentCreate(BaseModel):
    # min_length=1 → empty comments are rejected with 422 before our code runs.
    body: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    id: int
    card_id: int
    body: str
    author: UserBrief  # built from comment.author (a User) via from_attributes
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
