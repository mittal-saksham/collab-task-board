"""Pydantic schemas for users — the API's public contract for user data.

Remember: these are SEPARATE from the SQLAlchemy `User` model. The model is the
DB shape (includes hashed_password); these schemas decide what crosses the wire.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Body for POST /auth/signup. Pydantic validates these BEFORE our code runs."""

    # EmailStr rejects malformed emails automatically (needs email-validator pkg).
    email: EmailStr
    # min_length=8 -> a too-short password returns 422 without us writing checks.
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    """What we return ABOUT a user. Note: no password / hash field ever leaves here."""

    id: int
    email: EmailStr
    created_at: datetime

    # from_attributes=True lets FastAPI build this straight from a SQLAlchemy
    # User object (reading .id, .email, ...) instead of requiring a dict.
    model_config = ConfigDict(from_attributes=True)
