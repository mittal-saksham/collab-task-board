"""Board routes: create, list mine, view (with contents), edit, delete.

Every route requires a logged-in user (`CurrentUser`). Viewing/editing is gated
by board membership; editing/deleting additionally requires being the owner.
Mutations broadcast an event to anyone watching the board over WebSocket.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.core.ratelimit import summarize_limiter
from app.crud import board as board_crud
from app.db.session import get_db
from app.schemas.board import (
    BoardCreate,
    BoardDetail,
    BoardRead,
    BoardSummary,
    BoardUpdate,
)
from app.services import llm
from app.ws.manager import emit

logger = logging.getLogger(__name__)

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
    """Return a board with all its lists and cards (the full render payload).

    Calls the crud directly (not access.require_board_member) because this is
    the one route that wants the contents eager-loaded — the access helper does
    a contents-free lookup, which is right everywhere else.
    """
    board = board_crud.get_board_for_member(
        db, board_id, current_user.id, with_contents=True
    )
    if board is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


@router.patch("/{board_id}", response_model=BoardRead)
def update_board(
    board_id: int, payload: BoardUpdate, current_user: CurrentUser, db: DbSession
):
    """Rename a board. Owner only."""
    board = access.require_board_owner(db, board_id, current_user.id)
    board = board_crud.update_board(db, board, title=payload.title)
    emit(board.id, "board.updated", BoardRead.model_validate(board).model_dump(mode="json"))
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int, current_user: CurrentUser, db: DbSession):
    """Delete a board (and its lists/cards via cascade). Owner only."""
    board = access.require_board_owner(db, board_id, current_user.id)
    board_crud.delete_board(db, board)
    emit(board_id, "board.deleted", {"id": board_id})


@router.post(
    "/{board_id}/summarize",
    response_model=BoardSummary,
    dependencies=[Depends(summarize_limiter)],
)
def summarize_board(board_id: int, current_user: CurrentUser, db: DbSession):
    """Optional AI feature: a short LLM-written summary of the board.

    Any board member can use it — rate-limited, since each call costs real
    Anthropic API money. Returns 503 if the summarizer isn't configured
    (no ANTHROPIC_API_KEY), 502 if the LLM request fails.
    """
    board = access.require_board_member(db, board_id, current_user.id)
    try:
        summary = llm.summarize_board(board)
    except llm.SummarizerNotConfigured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summarizer is not configured. Set ANTHROPIC_API_KEY to enable it.",
        )
    except llm.SummarizerError:
        # Log the upstream detail server-side; don't reflect a raw provider
        # exception string to API clients.
        logger.exception("Board summarize failed (board_id=%s)", board.id)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="LLM request failed"
        )
    return BoardSummary(summary=summary)
