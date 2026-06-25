"""Card routes: create under a list, edit, delete, and move (drag-and-drop)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import card as card_crud
from app.crud import list as list_crud
from app.db.session import get_db
from app.schemas.card import CardCreate, CardMove, CardRead, CardUpdate

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
    access.require_list_access(db, list_id, current_user.id)
    return card_crud.create_card(
        db, list_id=list_id, title=payload.title, description=payload.description
    )


@router.patch("/cards/{card_id}", response_model=CardRead)
def update_card(
    card_id: int, payload: CardUpdate, current_user: CurrentUser, db: DbSession
):
    card = access.require_card_access(db, card_id, current_user.id)
    return card_crud.update_card(
        db, card, title=payload.title, description=payload.description
    )


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, current_user: CurrentUser, db: DbSession):
    card = access.require_card_access(db, card_id, current_user.id)
    card_crud.delete_card(db, card)


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

    return card_crud.move_card(
        db, card, target_list_id=payload.list_id, after_id=payload.after_id
    )
