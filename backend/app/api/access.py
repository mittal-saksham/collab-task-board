"""Shared authorization helpers for board-scoped resources.

Lists and cards don't carry their own permissions — access is decided by the
BOARD they ultimately belong to. These helpers resolve a resource, confirm the
user can access its board, and raise 404 otherwise (404 not 403, so we don't
reveal that a resource exists to someone who shouldn't see it).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import board as board_crud
from app.crud import card as card_crud
from app.crud import list as list_crud
from app.models.board import Board
from app.models.card import Card
from app.models.list import List


def _not_found(thing: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{thing} not found")


def require_board_member(db: Session, board_id: int, user_id: int) -> Board:
    board = board_crud.get_board_for_member(db, board_id, user_id)
    if board is None:
        raise _not_found("Board")
    return board


def require_board_owner(db: Session, board_id: int, user_id: int) -> Board:
    """Like require_board_member, but additionally requires being the OWNER.

    404 if you can't see the board at all; 403 if you can see it but aren't the
    owner (managing members is owner-only).
    """
    board = require_board_member(db, board_id, user_id)
    if board.owner_id != user_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the board owner can do this"
        )
    return board


def require_list_access(db: Session, list_id: int, user_id: int) -> List:
    lst = list_crud.get_list(db, list_id)
    if lst is None or board_crud.get_board_for_member(db, lst.board_id, user_id) is None:
        raise _not_found("List")
    return lst


def require_card_access(db: Session, card_id: int, user_id: int) -> Card:
    card = card_crud.get_card(db, card_id)
    if card is None:
        raise _not_found("Card")
    lst = list_crud.get_list(db, card.list_id)
    if lst is None or board_crud.get_board_for_member(db, lst.board_id, user_id) is None:
        raise _not_found("Card")
    return card
