"""Card routes: create under a list, edit, delete, and move (drag-and-drop).

Each mutation broadcasts a delta event to the board's WebSocket watchers. Card
events carry the board_id so the manager knows which room to push to (cards only
store list_id, so we resolve the board via the card's list).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import card as card_crud
from app.crud import list as list_crud
from app.crud import membership as membership_crud
from app.db.session import get_db
from app.schemas.card import CardCreate, CardMove, CardRead, CardUpdate
from app.services import activity_log
from app.ws.manager import emit


def _payload(card) -> dict:
    """Serialize a Card ORM object to a JSON-able dict for an event."""
    return CardRead.model_validate(card).model_dump(mode="json")


def _board_id_of(db: Session, card) -> int:
    """Resolve the board a card belongs to (via its list)."""
    return list_crud.get_list(db, card.list_id).board_id


def _short(text: str, n: int = 80) -> str:
    """Keep activity summaries tidy (titles can be up to 255 chars)."""
    return text if len(text) <= n else text[: n - 1] + "…"


router = APIRouter(tags=["cards"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/lists/{list_id}/cards",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    list_id: int, payload: CardCreate, current_user: CurrentUser, db: DbSession
):
    lst = access.require_list_access(db, list_id, current_user.id)
    card = card_crud.create_card(
        db, list_id=list_id, title=payload.title, description=payload.description
    )
    emit(lst.board_id, "card.created", _payload(card))
    activity_log.log(
        db,
        board_id=lst.board_id,
        actor_id=current_user.id,
        verb="created_card",
        summary=f'created card "{_short(card.title)}"',
        card_id=card.id,
    )
    return card


@router.patch("/cards/{card_id}", response_model=CardRead)
def update_card(
    card_id: int, payload: CardUpdate, current_user: CurrentUser, db: DbSession
):
    card = access.require_card_access(db, card_id, current_user.id)
    fields = payload.model_dump(exclude_unset=True)  # only the keys actually sent
    # If assigning someone (not unassigning), they must be a member of this board.
    if fields.get("assignee_id") is not None:
        board_id = _board_id_of(db, card)
        if membership_crud.get_membership(db, board_id, fields["assignee_id"]) is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of this board",
            )
    card = card_crud.update_card(db, card, fields)
    board_id = _board_id_of(db, card)
    emit(board_id, "card.updated", _payload(card))
    activity_log.log(
        db,
        board_id=board_id,
        actor_id=current_user.id,
        verb="updated_card",
        summary=f'updated "{_short(card.title)}"',
        card_id=card.id,
    )
    return card


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, current_user: CurrentUser, db: DbSession):
    card = access.require_card_access(db, card_id, current_user.id)
    board_id = _board_id_of(db, card)  # capture before deletion
    list_id = card.list_id
    title = card.title  # capture before the row is gone (for the activity line)
    card_crud.delete_card(db, card)
    emit(board_id, "card.deleted", {"id": card_id, "list_id": list_id})
    # card_id=None: the card no longer exists, so we can't FK-reference it.
    activity_log.log(
        db,
        board_id=board_id,
        actor_id=current_user.id,
        verb="deleted_card",
        summary=f'deleted card "{_short(title)}"',
    )


@router.patch("/cards/{card_id}/move", response_model=CardRead)
def move_card(
    card_id: int, payload: CardMove, current_user: CurrentUser, db: DbSession
):
    """Move/reorder a card. `list_id` is the target column, `after_id` the card to
    drop behind (None = front). Cross-board moves are rejected."""
    card = access.require_card_access(db, card_id, current_user.id)
    target_list = access.require_list_access(db, payload.list_id, current_user.id)

    # A card may only move within its own board (target list's board must match).
    current_list = list_crud.get_list(db, card.list_id)
    if target_list.board_id != current_list.board_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot move a card to another board"
        )

    if payload.after_id is not None:
        after = card_crud.get_card(db, payload.after_id)
        if after is None or after.list_id != target_list.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="after_id must be a card in the target list",
            )
        if after.id == card.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Cannot place a card after itself"
            )

    card = card_crud.move_card(
        db, card, target_list_id=payload.list_id, after_id=payload.after_id
    )
    emit(target_list.board_id, "card.moved", _payload(card))
    activity_log.log(
        db,
        board_id=target_list.board_id,
        actor_id=current_user.id,
        verb="moved_card",
        summary=f'moved "{_short(card.title)}" to {_short(target_list.title, 40)}',
        card_id=card.id,
    )
    return card
