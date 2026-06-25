"""Model package.

Importing every model HERE is what makes them visible to:
  - SQLAlchemy's registry (so relationships resolve string names like "Board"), and
  - Alembic autogenerate (which only sees tables whose models have been imported).

So elsewhere we can just `import app.models` and the whole schema is loaded.
"""

from app.db.base import Base
from app.models.board import Board
from app.models.card import Card
from app.models.list import List
from app.models.membership import Membership
from app.models.user import User

__all__ = ["Base", "User", "Board", "Membership", "List", "Card"]
