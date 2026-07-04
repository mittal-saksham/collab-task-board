"""Data-access for boards, including membership-based access checks."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.board import Board
from app.models.card import Card
from app.models.list import List
from app.models.membership import Membership


def create_board(db: Session, *, title: str, owner_id: int) -> Board:
    """Create a board AND the owner's membership row in a single transaction.

    Why both in one commit: our access queries read the `memberships` table, so a
    board without its owner-membership would be invisible to its own creator.
    """
    board = Board(title=title, owner_id=owner_id)
    db.add(board)
    db.flush()  # assigns board.id (sends the INSERT) without committing yet
    db.add(Membership(board_id=board.id, user_id=owner_id, role="owner"))
    db.commit()  # both rows are saved together (atomic)
    db.refresh(board)
    return board


def list_boards_for_user(db: Session, user_id: int) -> list[Board]:
    """All boards the user can access (owner or member) — one uniform query."""
    stmt = (
        select(Board)
        .join(Membership, Membership.board_id == Board.id)
        .where(Membership.user_id == user_id)
        .order_by(Board.created_at)
    )
    return list(db.execute(stmt).scalars().all())


def get_board_for_member(
    db: Session, board_id: int, user_id: int, *, with_contents: bool = False
) -> Board | None:
    """Return the board IF the user is a member/owner, else None.

    Returning None (→ 404 in the route) rather than 403 avoids revealing that a
    board exists to users who can't access it.

    `with_contents=True` eager-loads the full render payload (lists → cards →
    assignee/labels) in a handful of batched SELECT-IN queries. Only the board
    detail route wants this; every OTHER route calls this function purely as an
    access check, where loading a big board's contents would be pure waste —
    which is why eager loading is opt-in rather than the default. Without it,
    serializing BoardDetail lazy-loads per list and per card: ~200 queries for
    a 100-card board (the classic N+1).
    """
    stmt = (
        select(Board)
        .join(Membership, Membership.board_id == Board.id)
        .where(Board.id == board_id, Membership.user_id == user_id)
    )
    if with_contents:
        stmt = stmt.options(
            selectinload(Board.lists).selectinload(List.cards).selectinload(Card.assignee),
            selectinload(Board.lists).selectinload(List.cards).selectinload(Card.labels),
        )
    return db.execute(stmt).scalar_one_or_none()


def update_board(db: Session, board: Board, *, title: str) -> Board:
    board.title = title
    db.commit()
    db.refresh(board)
    return board


def delete_board(db: Session, board: Board) -> None:
    db.delete(board)  # cascades to memberships, lists, and cards (ON DELETE CASCADE)
    db.commit()
