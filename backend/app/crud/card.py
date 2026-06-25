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


def move_card(
    db: Session, card: Card, *, target_list_id: int, after_id: int | None
) -> Card:
    """Move `card` into `target_list_id`, after `after_id` (None = front).

    Same midpoint logic as lists, but scoped to the TARGET list and also updating
    `list_id` (which is what makes cross-column drag work).
    """
    if after_id is None:
        prev_position = None
        next_position = db.execute(
            select(func.min(Card.position)).where(
                Card.list_id == target_list_id, Card.id != card.id
            )
        ).scalar_one()
    else:
        after = db.get(Card, after_id)  # route guarantees it's in the target list
        prev_position = after.position
        next_position = db.execute(
            select(func.min(Card.position)).where(
                Card.list_id == target_list_id,
                Card.id != card.id,
                Card.position > after.position,
            )
        ).scalar_one()

    card.list_id = target_list_id
    card.position = ordering.position_between(prev_position, next_position)
    db.commit()
    db.refresh(card)
    return card
