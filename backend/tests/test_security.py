"""DB-backed tests for the security batch (docs/13): rate limiting, the
login timing equalizer's behavior contract, WS ticket auth, and the
board-detail query bound (the N+1 fix).
"""

import pytest
from starlette.websockets import WebSocketDisconnect


def _make_board(client, headers, title="Sprint"):
    r = client.post("/boards", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


# --- rate limiting ---


def test_login_rate_limited_after_10_attempts(client, auth):
    auth("victim@x.com")  # 1 signup + 1 login consumed from the limiters
    # Burn the remaining login budget with bad passwords.
    for _ in range(9):
        r = client.post(
            "/auth/login", data={"username": "victim@x.com", "password": "wrong-pass"}
        )
        assert r.status_code == 401
    # 11th login attempt in the window → throttled, with a Retry-After hint.
    r = client.post(
        "/auth/login", data={"username": "victim@x.com", "password": "wrong-pass"}
    )
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_signup_rate_limited(client):
    for i in range(10):
        r = client.post(
            "/auth/signup",
            json={"email": f"u{i}@x.com", "password": "supersecret123"},
        )
        assert r.status_code == 201
    r = client.post(
        "/auth/signup", json={"email": "u10@x.com", "password": "supersecret123"}
    )
    assert r.status_code == 429


def test_valid_requests_unaffected_under_the_limit(client, auth):
    # The auth fixture (signup+login) plus one more login stays well under 10.
    auth("fine@x.com")
    r = client.post(
        "/auth/login", data={"username": "fine@x.com", "password": "supersecret123"}
    )
    assert r.status_code == 200


# --- login behavior contract (the timing fix must not change semantics) ---


def test_login_unknown_email_still_generic_401(client):
    r = client.post(
        "/auth/login", data={"username": "ghost@x.com", "password": "whatever123"}
    )
    assert r.status_code == 401
    # Same message as wrong-password — no enumeration via the body either.
    assert r.json()["detail"] == "Incorrect email or password"


# --- WebSocket tickets ---


def test_ws_ticket_requires_auth(client):
    assert client.post("/auth/ws-ticket").status_code == 401


def test_ws_connect_with_ticket(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    ticket = client.post("/auth/ws-ticket", headers=owner).json()["ticket"]
    with client.websocket_connect(f"/ws/boards/{board['id']}?ticket={ticket}"):
        pass  # accepted — that's the assertion


def test_ws_ticket_is_single_use(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    ticket = client.post("/auth/ws-ticket", headers=owner).json()["ticket"]
    with client.websocket_connect(f"/ws/boards/{board['id']}?ticket={ticket}"):
        pass
    # Second redemption of the same ticket must be rejected.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/boards/{board['id']}?ticket={ticket}"):
            pass


def test_ws_garbage_ticket_rejected(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/boards/{board['id']}?ticket=not-a-ticket"):
            pass


def test_ws_nonmember_ticket_rejected(client, auth):
    """A perfectly valid ticket still doesn't grant access to someone else's board."""
    owner = auth("owner@x.com")
    stranger = auth("stranger@x.com")
    board = _make_board(client, owner)
    ticket = client.post("/auth/ws-ticket", headers=stranger).json()["ticket"]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/boards/{board['id']}?ticket={ticket}"):
            pass


# --- N+1 fix: board detail must issue a bounded number of queries ---


def test_board_detail_query_count_is_bounded(client, auth, _engine):
    """20 cards across 2 lists must NOT mean ~40+ queries.

    With selectinload the shape is: 1 board(+membership join) + 1 lists batch
    + 1 cards batch + 1 assignees batch + 1 labels batch (+ the association
    rows) — constant in the number of cards. Before the fix this request
    lazy-loaded per list and per card and the count grew linearly.
    """
    from sqlalchemy import event

    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    for list_title in ("Todo", "Doing"):
        r = client.post(
            f"/boards/{board['id']}/lists", json={"title": list_title}, headers=owner
        )
        list_id = r.json()["id"]
        for i in range(10):
            client.post(
                f"/lists/{list_id}/cards", json={"title": f"c{i}"}, headers=owner
            )

    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(_engine, "before_cursor_execute", count)
    try:
        r = client.get(f"/boards/{board['id']}", headers=owner)
        assert r.status_code == 200
        assert sum(len(l["cards"]) for l in r.json()["lists"]) == 20
    finally:
        event.remove(_engine, "before_cursor_execute", count)

    # Generous bound: the batched shape is ~5-7 SELECTs; the lazy N+1 shape
    # was 40+. The exact number may drift a little with ORM versions — the
    # point is it must not scale with card count.
    assert len(statements) <= 10, (
        f"{len(statements)} SELECTs for a 20-card board — N+1 is back?\n"
        + "\n".join(statements)
    )
