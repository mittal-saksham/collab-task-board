"""Activity feed route — read-only.

The rows themselves are written as a side-effect of OTHER routes (card create/
move/update/delete, comment, member add) via `app/services/activity_log.py`.
This endpoint just returns a board's recent feed. Any member may read it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import access
from app.api.deps import CurrentUser
from app.crud import activity as activity_crud
from app.db.session import get_db
from app.schemas.activity import ActivityRead

router = APIRouter(tags=["activity"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/boards/{board_id}/activities", response_model=list[ActivityRead])
def list_activities(board_id: int, current_user: CurrentUser, db: DbSession):
    access.require_board_member(db, board_id, current_user.id)
    return activity_crud.list_activities(db, board_id)
