"""Pydantic schema for the JWT we hand back at login."""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    # "bearer" is the standard scheme name; clients send `Authorization: Bearer <token>`.
    token_type: str = "bearer"


class WsTicket(BaseModel):
    """A single-use, ~60s ticket for opening a WebSocket (see ws/tickets.py)."""

    ticket: str
