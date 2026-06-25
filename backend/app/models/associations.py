"""Association tables for many-to-many relationships.

Kept in a standalone module (it imports only Base, no models) so the two models
that share a join table never have to import each other at module top — which
would create a circular import.
"""

from sqlalchemy import Column, ForeignKey, Table

from app.db.base import Base

card_labels = Table(
    "card_labels",
    Base.metadata,
    Column("card_id", ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)
