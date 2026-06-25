"""Comment routes: list, post, and delete comments on a card.

Any board member can read and post; only the comment's author can delete it.
Posting also writes an activity-feed entry. Both actions broadcast over the
board's WebSocket so other watchers update live.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import comment as comment_crud
from app.crud import list as list_crud
from app.db.session import get_db
from app.schemas.comment import CommentCreate, CommentRead
from app.services import activity_log
from app.ws.manager import emit

router = APIRouter(tags=["comments"])

DbSession = Annotated[Session, Depends(get_db)]


def _board_id_of_card(db: Session, card) -> int:
    return list_crud.get_list(db, card.list_id).board_id


def _truncate(text: str, n: int = 80) -> str:
    """Keep activity summaries short and tidy."""
    return text if len(text) <= n else text[: n - 1] + "…"


@router.get("/cards/{card_id}/comments", response_model=list[CommentRead])
def list_comments(card_id: int, current_user: CurrentUser, db: DbSession):
    access.require_card_access(db, card_id, current_user.id)
    return comment_crud.list_comments(db, card_id)


@router.post(
    "/cards/{card_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    card_id: int, payload: CommentCreate, current_user: CurrentUser, db: DbSession
):
    card = access.require_card_access(db, card_id, current_user.id)
    board_id = _board_id_of_card(db, card)
    comment = comment_crud.create_comment(
        db, card_id=card_id, author_id=current_user.id, body=payload.body
    )
    emit(
        board_id,
        "comment.created",
        CommentRead.model_validate(comment).model_dump(mode="json"),
    )
    activity_log.log(
        db,
        board_id=board_id,
        actor_id=current_user.id,
        verb="commented",
        summary=f'commented on "{_truncate(card.title)}"',
        card_id=card_id,
    )
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, current_user: CurrentUser, db: DbSession):
    comment = comment_crud.get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Comment not found")
    # Confirms the user can access the card's board (404 otherwise).
    card = access.require_card_access(db, comment.card_id, current_user.id)
    if comment.author_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You can only delete your own comments"
        )
    card_id = comment.card_id  # capture before delete (the row is about to go)
    board_id = _board_id_of_card(db, card)
    comment_crud.delete_comment(db, comment)
    emit(board_id, "comment.deleted", {"id": comment_id, "card_id": card_id})
