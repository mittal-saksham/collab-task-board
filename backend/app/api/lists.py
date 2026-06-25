"""List (column) routes: create under a board, rename, delete, reorder.

Each mutation broadcasts a delta event to the board's WebSocket watchers.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import list as list_crud
from app.db.session import get_db
from app.schemas.list import ListCreate, ListMove, ListRead, ListUpdate
from app.ws.manager import emit


def _payload(lst) -> dict:
    """Serialize a List ORM object to a JSON-able dict for an event."""
    return ListRead.model_validate(lst).model_dump(mode="json")


router = APIRouter(tags=["lists"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/boards/{board_id}/lists",
    response_model=ListRead,
    status_code=status.HTTP_201_CREATED,
)
def create_list(
    board_id: int, payload: ListCreate, current_user: CurrentUser, db: DbSession
):
    access.require_board_member(db, board_id, current_user.id)
    new_list = list_crud.create_list(db, board_id=board_id, title=payload.title)
    emit(board_id, "list.created", _payload(new_list))
    return new_list


@router.patch("/lists/{list_id}", response_model=ListRead)
def update_list(
    list_id: int, payload: ListUpdate, current_user: CurrentUser, db: DbSession
):
    lst = access.require_list_access(db, list_id, current_user.id)
    lst = list_crud.update_list(db, lst, title=payload.title)
    emit(lst.board_id, "list.updated", _payload(lst))
    return lst


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(list_id: int, current_user: CurrentUser, db: DbSession):
    lst = access.require_list_access(db, list_id, current_user.id)
    board_id = lst.board_id  # capture before the row is gone
    list_crud.delete_list(db, lst)
    emit(board_id, "list.deleted", {"id": list_id, "board_id": board_id})


@router.patch("/lists/{list_id}/move", response_model=ListRead)
def move_list(
    list_id: int, payload: ListMove, current_user: CurrentUser, db: DbSession
):
    """Reorder a list within its board (place it after `after_id`, or at front)."""
    lst = access.require_list_access(db, list_id, current_user.id)
    if payload.after_id is not None:
        after = list_crud.get_list(db, payload.after_id)
        if after is None or after.board_id != lst.board_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="after_id must be a list in the same board",
            )
        if after.id == lst.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Cannot place a list after itself"
            )
    lst = list_crud.move_list(db, lst, after_id=payload.after_id)
    emit(lst.board_id, "list.moved", _payload(lst))
    return lst
