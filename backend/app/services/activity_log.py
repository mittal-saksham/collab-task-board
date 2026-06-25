"""One call for routes to record a board activity AND broadcast it live.

Why a service (not just `crud.activity.record`)? Two reasons:
1. It bundles the DB write with the `activity.created` WebSocket broadcast, so
   every place that logs an event also notifies live watchers — consistently.
2. It is BEST-EFFORT: the whole thing is wrapped in try/except. Activity logging
   is a secondary concern; a bug here must never break the primary mutation
   (creating a card, posting a comment, …) that already committed. On failure we
   roll back just the activity insert and move on.
"""

from sqlalchemy.orm import Session

from app.crud import activity as activity_crud
from app.models.activity import Activity
from app.schemas.activity import ActivityRead
from app.ws.manager import emit


def log(
    db: Session,
    *,
    board_id: int,
    actor_id: int | None,
    verb: str,
    summary: str,
    card_id: int | None = None,
) -> Activity | None:
    try:
        activity = activity_crud.record(
            db,
            board_id=board_id,
            actor_id=actor_id,
            verb=verb,
            summary=summary,
            card_id=card_id,
        )
        emit(
            board_id,
            "activity.created",
            ActivityRead.model_validate(activity).model_dump(mode="json"),
        )
        return activity
    except Exception:
        # Never let a logging hiccup surface as a failed mutation.
        db.rollback()
        return None
