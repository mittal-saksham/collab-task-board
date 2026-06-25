"""Pydantic schemas for labels."""

from pydantic import BaseModel, ConfigDict, Field


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="slate", max_length=20)


class LabelRead(BaseModel):
    id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)
