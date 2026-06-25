"""Data-access for board memberships (invite / list / remove)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.membership import Membership


def get_membership(db: Session, board_id: int, user_id: int) -> Membership | None:
    return db.execute(
        select(Membership).where(
            Membership.board_id == board_id, Membership.user_id == user_id
        )
    ).scalar_one_or_none()


def add_member(db: Session, *, board_id: int, user_id: int, role: str = "member") -> Membership:
    membership = Membership(board_id=board_id, user_id=user_id, role=role)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def list_members(db: Session, board_id: int) -> list[Membership]:
    """All memberships of a board, oldest first. `.user` is lazy-loaded per row."""
    stmt = (
        select(Membership)
        .where(Membership.board_id == board_id)
        .order_by(Membership.created_at)
    )
    return list(db.execute(stmt).scalars().all())


def remove_member(db: Session, membership: Membership) -> None:
    db.delete(membership)
    db.commit()
