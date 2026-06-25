"""In-memory WebSocket connection manager + a broadcast bridge for sync code.

`manager` tracks which live sockets are watching which board (a "room" per
board). REST routes call `emit(...)` after a mutation to push a typed event to
everyone watching that board.

The bridge: our REST handlers run synchronously in a threadpool, but sockets
live on the asyncio event loop. `broadcast_from_sync` uses
`run_coroutine_threadsafe` to hop the broadcast back onto the loop.

NOTE: this state is in-memory and PER PROCESS. Running multiple backend
instances would need a shared pub/sub (e.g. Redis) so an event reaches sockets
connected to other instances. One instance is fine for the MVP.
"""

import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # board_id -> set of sockets currently watching that board
        self._rooms: dict[int, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the running event loop (called once, on app startup)."""
        self._loop = loop

    async def connect(self, board_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms.setdefault(board_id, set()).add(websocket)

    def disconnect(self, board_id: int, websocket: WebSocket) -> None:
        room = self._rooms.get(board_id)
        if not room:
            return
        room.discard(websocket)
        if not room:  # drop empty rooms so the dict doesn't grow forever
            self._rooms.pop(board_id, None)

    async def broadcast(self, board_id: int, message: dict) -> None:
        """Send `message` as JSON to every socket watching the board."""
        dead: list[WebSocket] = []
        for websocket in list(self._rooms.get(board_id, set())):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)  # socket died mid-send; clean it up
        for websocket in dead:
            self.disconnect(board_id, websocket)

    def broadcast_from_sync(self, board_id: int, message: dict) -> None:
        """Schedule a broadcast from synchronous (threadpool) route code."""
        if self._loop is None:
            return  # app not fully started yet; nothing to broadcast to
        asyncio.run_coroutine_threadsafe(
            self.broadcast(board_id, message), self._loop
        )


# A single shared manager instance used across the whole app.
manager = ConnectionManager()


def emit(board_id: int, event_type: str, data: dict) -> None:
    """Broadcast a typed event (e.g. "card.moved") to a board's watchers."""
    manager.broadcast_from_sync(board_id, {"type": event_type, "data": data})
