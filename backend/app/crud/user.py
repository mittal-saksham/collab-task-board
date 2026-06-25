"""Data-access functions for users (the "CRUD" / repository layer).

Routes call these instead of touching the DB directly, so DB logic stays in one
place and is testable without HTTP. All queries use the SQLAlchemy 2.0 `select()`
style (not legacy `.query()`), which is identical for sync and async.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the user with this email, or None. Used on signup + login."""
    # scalar_one_or_none() -> exactly one User object, or None if no row matched.
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return the user with this id, or None. Used when validating a JWT."""
    # db.get() is the fast path for primary-key lookups (checks the identity map).
    return db.get(User, user_id)


def create_user(db: Session, email: str, password: str) -> User:
    """Hash the password, insert the user, and return the saved row."""
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)          # stage the INSERT
    db.commit()           # write it to the DB
    db.refresh(user)      # reload server-generated fields (id, created_at)
    return user
