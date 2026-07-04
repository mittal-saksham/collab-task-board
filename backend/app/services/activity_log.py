"""One call for routes to record a board activity AND broadcast it live.

Why a service (not just `crud.activity.record`)? Two reasons:
1. It bundles the DB write with the `activity.created` WebSocket broadcast, so
   every place that logs an event also notifies live watchers — consistently.
2. It is BEST-EFFORT: the whole thing is wrapped in try/except. Activity logging
   is a secondary concern; a bug here must never break the primary mutation
   (creating a card, posting a comment, …) that already committed. On failure we
   roll back just the activity insert and move on.
"""

import logging

from sqlalchemy.orm import Session

from app.crud import activity as activity_crud
from app.models.activity import Activity
from app.schemas.activity import ActivityRead
from app.ws.manager import emit

logger = logging.getLogger(__name__)


def short(text: str, n: int = 80) -> str:
    """Keep activity summaries tidy (titles can be up to 255 chars)."""
    return text if len(text) <= n else text[: n - 1] + "…"


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
        # Never let a logging hiccup surface as a failed mutation — but DO leave
        # an operator signal: a permanent bug here would otherwise silence the
        # entire activity feed with no trace anywhere.
        logger.exception("Failed to record activity (board_id=%s, verb=%s)", board_id, verb)
        db.rollback()
        return None
