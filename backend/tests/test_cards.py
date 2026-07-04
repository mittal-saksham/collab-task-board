"""DB-backed tests for card routes: move/rebalance, PATCH semantics, and authz.

Covers the two fixes from the repo review:
  - the rebalance fallback (repeated same-gap moves must not corrupt ordering)
  - explicit `null` on NOT NULL fields must 422, not 500
plus the card-level access-control coverage that test_access.py (boards only)
was missing.
"""


def _make_board(client, headers, title="Sprint"):
    r = client.post("/boards", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


def _make_list(client, headers, board_id, title="Todo"):
    r = client.post(f"/boards/{board_id}/lists", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


def _make_card(client, headers, list_id, title):
    r = client.post(f"/lists/{list_id}/cards", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


def _board_card_titles(client, headers, board_id, list_id):
    """The card titles of one list, in the order the API returns them."""
    r = client.get(f"/boards/{board_id}", headers=headers)
    assert r.status_code == 200
    (lst,) = [l for l in r.json()["lists"] if l["id"] == list_id]
    return [c["title"] for c in lst["cards"]]


# --- move + rebalance ---


def test_repeated_moves_into_same_gap_stay_ordered(client, auth):
    """The float-precision scenario: drop a card into the same slot ~60 times.

    Without the rebalance fallback, midpoints stop producing distinct values
    after ~50 iterations and two cards silently collide. With it, positions must
    stay distinct and the visible order must stay correct throughout.
    """
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    lst = _make_list(client, owner, board["id"])
    a = _make_card(client, owner, lst["id"], "A")
    b = _make_card(client, owner, lst["id"], "B")
    c = _make_card(client, owner, lst["id"], "C")

    # Repeatedly move C right after A: every midpoint lands in the same
    # ever-shrinking (A, previous-C) gap.
    for i in range(60):
        r = client.patch(
            f"/cards/{c['id']}/move",
            json={"list_id": lst["id"], "after_id": a["id"]},
            headers=owner,
        )
        assert r.status_code == 200, f"move {i} failed: {r.json()}"

    # Order is still A, C, B and no two cards share a position.
    assert _board_card_titles(client, owner, board["id"], lst["id"]) == ["A", "C", "B"]
    r = client.get(f"/boards/{board['id']}", headers=owner)
    positions = [
        card["position"] for l in r.json()["lists"] for card in l["cards"]
    ]
    assert len(set(positions)) == len(positions)
    assert b["id"] and positions == sorted(positions)


def test_move_to_front_and_back(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    lst = _make_list(client, owner, board["id"])
    _make_card(client, owner, lst["id"], "A")
    b = _make_card(client, owner, lst["id"], "B")
    c = _make_card(client, owner, lst["id"], "C")

    # after_id=null -> front.
    r = client.patch(
        f"/cards/{c['id']}/move",
        json={"list_id": lst["id"], "after_id": None},
        headers=owner,
    )
    assert r.status_code == 200
    assert _board_card_titles(client, owner, board["id"], lst["id"]) == ["C", "A", "B"]

    # after the current last card -> back.
    r = client.patch(
        f"/cards/{c['id']}/move",
        json={"list_id": lst["id"], "after_id": b["id"]},
        headers=owner,
    )
    assert r.status_code == 200
    assert _board_card_titles(client, owner, board["id"], lst["id"]) == ["A", "B", "C"]


def test_cross_list_move(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    todo = _make_list(client, owner, board["id"], "Todo")
    done = _make_list(client, owner, board["id"], "Done")
    a = _make_card(client, owner, todo["id"], "A")

    r = client.patch(
        f"/cards/{a['id']}/move",
        json={"list_id": done["id"], "after_id": None},
        headers=owner,
    )
    assert r.status_code == 200
    assert r.json()["list_id"] == done["id"]
    assert _board_card_titles(client, owner, board["id"], done["id"]) == ["A"]


# --- PATCH null semantics ---


def test_patch_null_title_is_422_not_500(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    lst = _make_list(client, owner, board["id"])
    card = _make_card(client, owner, lst["id"], "A")

    for field in ("title", "priority", "issue_type"):
        r = client.patch(f"/cards/{card['id']}", json={field: None}, headers=owner)
        assert r.status_code == 422, f"{field}: expected 422, got {r.status_code}"

    # List titles are NOT NULL too.
    r = client.patch(f"/lists/{lst['id']}", json={"title": None}, headers=owner)
    assert r.status_code == 422


def test_patch_null_still_clears_nullable_fields(client, auth):
    """The clear-with-null convention must keep working for nullable fields."""
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    lst = _make_list(client, owner, board["id"])
    card = _make_card(client, owner, lst["id"], "A")

    r = client.patch(
        f"/cards/{card['id']}", json={"story_points": 5}, headers=owner
    )
    assert r.status_code == 200 and r.json()["story_points"] == 5
    r = client.patch(
        f"/cards/{card['id']}", json={"story_points": None}, headers=owner
    )
    assert r.status_code == 200 and r.json()["story_points"] is None


# --- card-level access control (was untested; boards-only before) ---


def test_nonmember_cannot_touch_cards(client, auth):
    owner = auth("owner@x.com")
    stranger = auth("stranger@x.com")
    board = _make_board(client, owner)
    lst = _make_list(client, owner, board["id"])
    card = _make_card(client, owner, lst["id"], "A")

    # 404 (not 403) everywhere: don't reveal the card exists.
    assert (
        client.post(
            f"/lists/{lst['id']}/cards", json={"title": "X"}, headers=stranger
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/cards/{card['id']}", json={"title": "X"}, headers=stranger
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/cards/{card['id']}/move",
            json={"list_id": lst["id"], "after_id": None},
            headers=stranger,
        ).status_code
        == 404
    )
    assert client.delete(f"/cards/{card['id']}", headers=stranger).status_code == 404


def test_move_to_another_boards_list_is_rejected(client, auth):
    """A member of both boards still can't drag a card across boards."""
    owner = auth("owner@x.com")
    board1 = _make_board(client, owner, "One")
    board2 = _make_board(client, owner, "Two")
    lst1 = _make_list(client, owner, board1["id"])
    lst2 = _make_list(client, owner, board2["id"])
    card = _make_card(client, owner, lst1["id"], "A")

    r = client.patch(
        f"/cards/{card['id']}/move",
        json={"list_id": lst2["id"], "after_id": None},
        headers=owner,
    )
    assert r.status_code == 400
