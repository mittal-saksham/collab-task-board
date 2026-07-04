"""WebSocket endpoint for live board updates.

A client opens `WS /ws/boards/{board_id}?ticket=<ticket>` to subscribe, where
the ticket is a single-use short-lived credential from `POST /auth/ws-ticket`
(see ws/tickets.py — the JWT itself never goes in a URL, so it can't leak into
access logs). The server redeems the ticket + checks board access, then keeps
the socket open and pushes events (card.moved, list.created, ...) as other
users change the board.
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.crud import board as board_crud
from app.db.session import SessionLocal
from app.ws import tickets
from app.ws.manager import manager

router = APIRouter()


def _authorize(ticket: str, board_id: int) -> bool:
    """Redeem the ticket (single-use!) and check the user can access the board.

    We open a short-lived DB session just for this check (rather than the request
    `get_db` dependency) so we don't hold a session open for the whole socket.
    """
    user_id = tickets.redeem(ticket)
    if user_id is None:
        return False
    db = SessionLocal()
    try:
        return board_crud.get_board_for_member(db, board_id, user_id) is not None
    finally:
        db.close()


@router.websocket("/ws/boards/{board_id}")
async def board_ws(
    websocket: WebSocket, board_id: int, ticket: str = Query(...)
) -> None:
    # Validate BEFORE accepting the connection.
    if not _authorize(ticket, board_id):
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
