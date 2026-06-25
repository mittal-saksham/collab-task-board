"""Pydantic schemas for board membership."""

from pydantic import BaseModel, EmailStr


class MemberInvite(BaseModel):
    """Body for inviting someone: just the email of an EXISTING user."""

    email: EmailStr


class MemberRead(BaseModel):
    """A board member as returned by the API (flattens membership + user)."""

    user_id: int
    email: EmailStr
    role: str
