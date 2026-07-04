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


# Only these fields can be set through update_list (whitelist — never trust
# arbitrary keys from the request).
_UPDATABLE_FIELDS = ("title", "wip_limit")


def update_list(db: Session, lst: List, fields: dict) -> List:
    """Apply only the provided fields (the route passes model_dump(exclude_unset=True),
    so a present `wip_limit: None` clears the limit; an absent key is left alone)."""
    for key in _UPDATABLE_FIELDS:
        if key in fields:
            setattr(lst, key, fields[key])
    db.commit()
    db.refresh(lst)
    return lst


def delete_list(db: Session, lst: List) -> None:
    db.delete(lst)  # cascades to its cards
    db.commit()


def _neighbour_positions(
    db: Session, *, board_id: int, list_id: int, after_id: int | None
) -> tuple[float | None, float | None]:
    """The (prev, next) positions surrounding the drop spot within the board."""
    if after_id is None:
        # Front of the board: no previous neighbour; next = current first list.
        prev_position = None
        next_position = db.execute(
            select(func.min(List.position)).where(
                List.board_id == board_id, List.id != list_id
            )
        ).scalar_one()
    else:
        after = db.get(List, after_id)  # route guarantees it's in the same board
        prev_position = after.position
        # next = the sibling immediately after `after` (smallest position greater
        # than after's), excluding the list being moved.
        next_position = db.execute(
            select(func.min(List.position)).where(
                List.board_id == board_id,
                List.id != list_id,
                List.position > after.position,
            )
        ).scalar_one()
    return prev_position, next_position


def _rebalance_board_lists(db: Session, *, board_id: int, exclude_list_id: int) -> None:
    """Renumber a board's lists when midpoint inserts have exhausted a gap."""
    siblings = (
        db.execute(
            select(List)
            .where(List.board_id == board_id, List.id != exclude_list_id)
            .order_by(List.position, List.id)
        )
        .scalars()
        .all()
    )
    for sib, pos in zip(siblings, ordering.rebalanced_positions(len(siblings))):
        sib.position = pos
    db.flush()


def move_list(db: Session, lst: List, *, after_id: int | None) -> List:
    """Reorder `lst` within its board, placing it after `after_id` (None = front).

    We compute the positions of the neighbours at the drop spot, then set this
    list's position to the midpoint — a single-row update, except in the rare
    case where the gap is exhausted and the board's lists get renumbered first.
    """
    prev_position, next_position = _neighbour_positions(
        db, board_id=lst.board_id, list_id=lst.id, after_id=after_id
    )
    if ordering.gap_exhausted(prev_position, next_position):
        _rebalance_board_lists(db, board_id=lst.board_id, exclude_list_id=lst.id)
        prev_position, next_position = _neighbour_positions(
            db, board_id=lst.board_id, list_id=lst.id, after_id=after_id
        )

    lst.position = ordering.position_between(prev_position, next_position)
    db.commit()
    db.refresh(lst)
    return lst
