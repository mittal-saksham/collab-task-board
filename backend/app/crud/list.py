"""Data-access for lists (columns), including reorder logic."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import ordering
from app.models.list import List


def get_list(db: Session, list_id: int) -> List | None:
    return db.get(List, list_id)


def create_list(db: Session, *, board_id: int, title: str) -> List:
    """Create a list at the END of the board's columns."""
    # max(position) among existing lists in this board (None if board has none).
    last_position = db.execute(
        select(func.max(List.position)).where(List.board_id == board_id)
    ).scalar_one()
    new_list = List(
        board_id=board_id,
        title=title,
        position=ordering.position_at_end(last_position),
    )
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    return new_list


def update_list(db: Session, lst: List, *, title: str) -> List:
    lst.title = title
    db.commit()
    db.refresh(lst)
    return lst


def delete_list(db: Session, lst: List) -> None:
    db.delete(lst)  # cascades to its cards
    db.commit()


def move_list(db: Session, lst: List, *, after_id: int | None) -> List:
    """Reorder `lst` within its board, placing it after `after_id` (None = front).

    We compute the positions of the neighbours at the drop spot, then set this
    list's position to the midpoint — a single-row update.
    """
    if after_id is None:
        # Front of the board: no previous neighbour; next = current first list.
        prev_position = None
        next_position = db.execute(
            select(func.min(List.position)).where(
                List.board_id == lst.board_id, List.id != lst.id
            )
        ).scalar_one()
    else:
        after = db.get(List, after_id)  # route guarantees it's in the same board
        prev_position = after.position
        # next = the sibling immediately after `after` (smallest position greater
        # than after's), excluding the list being moved.
        next_position = db.execute(
            select(func.min(List.position)).where(
                List.board_id == lst.board_id,
                List.id != lst.id,
                List.position > after.position,
            )
        ).scalar_one()

    lst.position = ordering.position_between(prev_position, next_position)
    db.commit()
    db.refresh(lst)
    return lst
