"""Declarative base for all ORM models.

Every database model (User, Board, List, Card, ...) will inherit from `Base`.
SQLAlchemy uses this shared base to keep a registry of all tables, which is how
tools like Alembic later "see" your whole schema.

We use the SQLAlchemy 2.0 `DeclarativeBase` class (not the older
`declarative_base()` function) because the 2.0 style is identical for sync and
async — exactly what we want for our planned sync -> async switch.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
