"""WebSocket endpoint for live board updates.

A client opens `WS /ws/boards/{board_id}?token=<jwt>` to subscribe. The server
validates the token + board access, then keeps the socket open and pushes events
(card.moved, list.created, ...) as other users change the board.
"""

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.crud import board as board_crud
from app.crud import user as user_crud
from app.db.session import SessionLocal
from app.models.user import User
from app.ws.manager import manager

router = APIRouter()


def _authenticate(token: str, board_id: int) -> User | None:
    """Return the user iff the token is valid AND they can access the board.

    We open a short-lived DB session just for this check (rather than the request
    `get_db` dependency) so we don't hold a session open for the whole socket.
    """
    db = SessionLocal()
    try:
        try:
            payload = decode_access_token(token)
            user = user_crud.get_user_by_id(db, int(payload.get("sub")))
        except (jwt.PyJWTError, TypeError, ValueError):
            return None
        if user is None:
            return None
        if board_crud.get_board_for_member(db, board_id, user.id) is None:
            return None
        return user
    finally:
        db.close()


@router.websocket("/ws/boards/{board_id}")
async def board_ws(
    websocket: WebSocket, board_id: int, token: str = Query(...)
) -> None:
    # The browser can't set an Authorization header on a WS handshake, so the
    # JWT arrives as a query param. Validate BEFORE accepting the connection.
    if _authenticate(token, board_id) is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)  # reject
        return

    await manager.connect(board_id, websocket)
    try:
        # The server only pushes; this loop just keeps the socket alive and
        # notices when the client goes away.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(board_id, websocket)
