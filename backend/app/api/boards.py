"""Board routes: create, list mine, view (with contents), edit, delete.

Every route requires a logged-in user (`CurrentUser`). Viewing/editing is gated
by board membership; editing/deleting additionally requires being the owner.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.crud import board as board_crud
from app.db.session import get_db
from app.schemas.board import BoardCreate, BoardDetail, BoardRead, BoardUpdate

router = APIRouter(prefix="/boards", tags=["boards"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=BoardRead, status_code=status.HTTP_201_CREATED)
def create_board(payload: BoardCreate, current_user: CurrentUser, db: DbSession):
    """Create a board owned by the current user (also adds the owner membership)."""
    return board_crud.create_board(db, title=payload.title, owner_id=current_user.id)


@router.get("", response_model=list[BoardRead])
def list_boards(current_user: CurrentUser, db: DbSession):
    """List every board the current user owns or is a member of."""
    return board_crud.list_boards_for_user(db, current_user.id)


@router.get("/{board_id}", response_model=BoardDetail)
def get_board(board_id: int, current_user: CurrentUser, db: DbSession):
    """Return a board with all its lists and cards (the full render payload)."""
    board = board_crud.get_board_for_member(db, board_id, current_user.id)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


@router.patch("/{board_id}", response_model=BoardRead)
def update_board(
    board_id: int, payload: BoardUpdate, current_user: CurrentUser, db: DbSession
):
    """Rename a board. Owner only."""
    board = board_crud.get_board_for_member(db, board_id, current_user.id)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the board owner can edit it"
        )
    return board_crud.update_board(db, board, title=payload.title)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a board (and its lists/cards via cascade). Owner only."""
    board = board_crud.get_board_for_member(db, board_id, current_user.id)
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the board owner can delete it"
        )
    board_crud.delete_board(db, board)
