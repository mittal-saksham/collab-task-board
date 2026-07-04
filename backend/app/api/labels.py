"""Label routes: manage a board's labels and attach/detach them to cards."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import label as label_crud
from app.db.session import get_db
from app.schemas.card import CardRead
from app.schemas.label import LabelCreate, LabelRead
from app.ws.manager import emit

router = APIRouter(tags=["labels"])

DbSession = Annotated[Session, Depends(get_db)]


# --- Board labels ---

@router.get("/boards/{board_id}/labels", response_model=list[LabelRead])
def list_labels(board_id: int, current_user: CurrentUser, db: DbSession):
    access.require_board_member(db, board_id, current_user.id)
    return label_crud.list_labels(db, board_id)


@router.post(
    "/boards/{board_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
def create_label(
    board_id: int, payload: LabelCreate, current_user: CurrentUser, db: DbSession
):
    access.require_board_member(db, board_id, current_user.id)
    label = label_crud.create_label(
        db, board_id=board_id, name=payload.name, color=payload.color
    )
    emit(board_id, "label.created", LabelRead.model_validate(label).model_dump(mode="json"))
    return label


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_label(label_id: int, current_user: CurrentUser, db: DbSession):
    label = label_crud.get_label(db, label_id)
    if label is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Label not found")
    access.require_board_member(db, label.board_id, current_user.id)
    board_id = label.board_id
    label_crud.delete_label(db, label)
    emit(board_id, "label.deleted", {"id": label_id})


# --- Attach / detach a label on a card ---

@router.put("/cards/{card_id}/labels/{label_id}", response_model=CardRead)
def attach_label(
    card_id: int, label_id: int, current_user: CurrentUser, db: DbSession
):
    card = access.require_card_access(db, card_id, current_user.id)
    label = label_crud.get_label(db, label_id)
    board_id = access.board_id_of_card(db, card)
    if label is None or label.board_id != board_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Label must belong to this board"
        )
    card = label_crud.attach_label(db, card, label)
    emit(board_id, "card.updated", CardRead.model_validate(card).model_dump(mode="json"))
    return card


@router.delete("/cards/{card_id}/labels/{label_id}", response_model=CardRead)
def detach_label(
    card_id: int, label_id: int, current_user: CurrentUser, db: DbSession
):
    card = access.require_card_access(db, card_id, current_user.id)
    label = label_crud.get_label(db, label_id)
    if label is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Label not found")
    card = label_crud.detach_label(db, card, label)
    emit(access.board_id_of_card(db, card), "card.updated",
         CardRead.model_validate(card).model_dump(mode="json"))
    return card
