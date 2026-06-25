"""Data-access for labels and card↔label attachment."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.label import Label


def list_labels(db: Session, board_id: int) -> list[Label]:
    stmt = select(Label).where(Label.board_id == board_id).order_by(Label.id)
    return list(db.execute(stmt).scalars().all())


def get_label(db: Session, label_id: int) -> Label | None:
    return db.get(Label, label_id)


def create_label(db: Session, *, board_id: int, name: str, color: str) -> Label:
    label = Label(board_id=board_id, name=name, color=color)
    db.add(label)
    db.commit()
    db.refresh(label)
    return label


def delete_label(db: Session, label: Label) -> None:
    db.delete(label)  # card_labels rows cascade away
    db.commit()


def attach_label(db: Session, card: Card, label: Label) -> Card:
    if label not in card.labels:
        card.labels.append(label)
        db.commit()
        db.refresh(card)
    return card


def detach_label(db: Session, card: Card, label: Label) -> Card:
    if label in card.labels:
        card.labels.remove(label)
        db.commit()
        db.refresh(card)
    return card
