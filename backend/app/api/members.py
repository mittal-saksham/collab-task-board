"""Membership routes: invite an existing user, list members, remove a member.

Inviting/removing is owner-only; listing is open to any member. Membership
changes broadcast over WebSocket so the board's watchers see them live.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import membership as membership_crud
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.member import MemberInvite, MemberRead
from app.ws.manager import emit

# board_id is part of the prefix, so every handler receives it as a path param.
router = APIRouter(prefix="/boards/{board_id}/members", tags=["members"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[MemberRead])
def list_members(board_id: int, current_user: CurrentUser, db: DbSession):
    """List a board's members. Any member may view this."""
    access.require_board_member(db, board_id, current_user.id)
    members = membership_crud.list_members(db, board_id)
    return [
        MemberRead(user_id=m.user_id, email=m.user.email, role=m.role)
        for m in members
    ]


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def add_member(
    board_id: int, payload: MemberInvite, current_user: CurrentUser, db: DbSession
):
    """Invite an existing user (by email) to the board. Owner only."""
    access.require_board_owner(db, board_id, current_user.id)

    user = user_crud.get_user_by_email(db, payload.email)
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="No user with that email"
        )
    if membership_crud.get_membership(db, board_id, user.id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="User is already a member"
        )

    membership = membership_crud.add_member(db, board_id=board_id, user_id=user.id)
    member = MemberRead(user_id=user.id, email=user.email, role=membership.role)
    emit(board_id, "member.added", member.model_dump(mode="json"))
    return member


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    board_id: int, user_id: int, current_user: CurrentUser, db: DbSession
):
    """Remove a member from the board. Owner only; the owner can't be removed."""
    board = access.require_board_owner(db, board_id, current_user.id)
    if user_id == board.owner_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot remove the board owner"
        )
    membership = membership_crud.get_membership(db, board_id, user_id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found")
    membership_crud.remove_member(db, membership)
    emit(board_id, "member.removed", {"user_id": user_id})
