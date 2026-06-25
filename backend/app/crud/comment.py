"""Data-access for comments."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment


def list_comments(db: Session, card_id: int) -> list[Comment]:
    """A card's comments, oldest first (chat-style reading order)."""
    stmt = (
        select(Comment)
        .where(Comment.card_id == card_id)
        .order_by(Comment.created_at, Comment.id)
    )
    return list(db.execute(stmt).scalars().all())


def get_comment(db: Session, comment_id: int) -> Comment | None:
    return db.get(Comment, comment_id)


def create_comment(db: Session, *, card_id: int, author_id: int, body: str) -> Comment:
    comment = Comment(card_id=card_id, author_id=author_id, body=body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: Comment) -> None:
    db.delete(comment)
    db.commit()
