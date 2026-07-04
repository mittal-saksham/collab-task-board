"""Data-access for cards, including move/reorder logic.

A "move" is the heart of the drag-and-drop feature: it can change a card's list
(across columns) and/or its position (reorder), and it's always a single-row
update thanks to fractional positions.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import ordering
from app.models.card import Card


def get_card(db: Session, card_id: int) -> Card | None:
    return db.get(Card, card_id)


def create_card(
    db: Session, *, list_id: int, title: str, description: str | None
) -> Card:
    """Create a card at the END of the list."""
    last_position = db.execute(
        select(func.max(Card.position)).where(Card.list_id == list_id)
    ).scalar_one()
    new_card = Card(
        list_id=list_id,
        title=title,
        description=description,
        position=ordering.position_at_end(last_position),
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card


# Only these fields can be set through update_card (whitelist — never trust
# arbitrary keys from the request).
_UPDATABLE_FIELDS = (
    "title",
    "description",
    "priority",
    "due_date",
    "assignee_id",
    "issue_type",
    "story_points",
)


def update_card(db: Session, card: Card, fields: dict) -> Card:
    """Apply only the provided fields (the route passes `model_dump(exclude_unset=True)`,
    so a present `assignee_id: None` unassigns, while an absent key is left alone)."""
    for key in _UPDATABLE_FIELDS:
        if key in fields:
            setattr(card, key, fields[key])
    db.commit()
    db.refresh(card)
    return card


def delete_card(db: Session, card: Card) -> None:
    db.delete(card)
    db.commit()


def _neighbour_positions(
    db: Session, *, target_list_id: int, card_id: int, after_id: int | None
) -> tuple[float | None, float | None]:
    """The (prev, next) positions surrounding the drop spot in the target list."""
    if after_id is None:
        prev_position = None
        next_position = db.execute(
            select(func.min(Card.position)).where(
                Card.list_id == target_list_id, Card.id != card_id
            )
        ).scalar_one()
    else:
        after = db.get(Card, after_id)  # route guarantees it's in the target list
        prev_position = after.position
        next_position = db.execute(
            select(func.min(Card.position)).where(
                Card.list_id == target_list_id,
                Card.id != card_id,
                Card.position > after.position,
            )
        ).scalar_one()
    return prev_position, next_position


def _rebalance_list(db: Session, *, list_id: int, exclude_card_id: int) -> None:
    """Renumber a list's cards to fresh evenly-spaced positions.

    Called when repeated midpoint inserts have exhausted the gap between two
    neighbours (float precision). Keeps the current order (id breaks ties, same
    as the read path) and flushes so the neighbour re-read sees the new values.
    """
    cards = (
        db.execute(
            select(Card)
            .where(Card.list_id == list_id, Card.id != exclude_card_id)
            .order_by(Card.position, Card.id)
        )
        .scalars()
        .all()
    )
    for c, pos in zip(cards, ordering.rebalanced_positions(len(cards))):
        c.position = pos
    db.flush()


def move_card(
    db: Session, card: Card, *, target_list_id: int, after_id: int | None
) -> Card:
    """Move `card` into `target_list_id`, after `after_id` (None = front).

    Same midpoint logic as lists, but scoped to the TARGET list and also updating
    `list_id` (which is what makes cross-column drag work). When the drop spot's
    gap is exhausted, the target list is renumbered first (the rebalance fallback).
    """
    prev_position, next_position = _neighbour_positions(
        db, target_list_id=target_list_id, card_id=card.id, after_id=after_id
    )
    if ordering.gap_exhausted(prev_position, next_position):
        _rebalance_list(db, list_id=target_list_id, exclude_card_id=card.id)
        prev_position, next_position = _neighbour_positions(
            db, target_list_id=target_list_id, card_id=card.id, after_id=after_id
        )

    card.list_id = target_list_id
    card.position = ordering.position_between(prev_position, next_position)
    db.commit()
    db.refresh(card)
    return card
