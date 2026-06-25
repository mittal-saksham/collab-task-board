"""Data-access for the activity feed.

Writing happens through `record(...)`; reading returns the most recent N events.
Routes don't usually call `record` directly — they go through
`app/services/activity_log.py`, which also broadcasts the event live.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity


def list_activities(db: Session, board_id: int, limit: int = 50) -> list[Activity]:
    """The board's most recent activity, newest first."""
    stmt = (
        select(Activity)
        .where(Activity.board_id == board_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def record(
    db: Session,
    *,
    board_id: int,
    actor_id: int | None,
    verb: str,
    summary: str,
    card_id: int | None = None,
) -> Activity:
    activity = Activity(
        board_id=board_id,
        actor_id=actor_id,
        verb=verb,
        summary=summary,
        card_id=card_id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity
