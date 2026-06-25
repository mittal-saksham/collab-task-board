"""DB-backed tests for board access control.

These exercise the authz rules the whole app leans on (api/access.py + the board
routes): membership gates *viewing* (404 to non-members, so we don't even reveal a
board exists), and ownership gates *editing/deleting* (403 to members who aren't
the owner).
"""


def _make_board(client, headers, title="Sprint"):
    r = client.post("/boards", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()


def test_owner_can_view_own_board(client, auth):
    owner = auth("owner@x.com")
    board = _make_board(client, owner)
    r = client.get(f"/boards/{board['id']}", headers=owner)
    assert r.status_code == 200
    assert r.json()["title"] == "Sprint"


def test_nonmember_gets_404_not_403(client, auth):
    owner = auth("owner@x.com")
    stranger = auth("stranger@x.com")
    board = _make_board(client, owner)
    # 404 (not 403): we don't reveal the board exists to someone who can't see it.
    assert client.get(f"/boards/{board['id']}", headers=stranger).status_code == 404


def test_added_member_can_view(client, auth):
    owner = auth("owner@x.com")
    member = auth("member@x.com")  # account must exist before it can be invited
    board = _make_board(client, owner)
    add = client.post(
        f"/boards/{board['id']}/members",
        json={"email": "member@x.com"},
        headers=owner,
    )
    assert add.status_code == 201
    assert client.get(f"/boards/{board['id']}", headers=member).status_code == 200


def test_member_cannot_rename_board_403(client, auth):
    owner = auth("owner@x.com")
    member = auth("member@x.com")
    board = _make_board(client, owner)
    client.post(
        f"/boards/{board['id']}/members",
        json={"email": "member@x.com"},
        headers=owner,
    )
    # A member can see the board but isn't the owner → editing is 403.
    r = client.patch(
        f"/boards/{board['id']}", json={"title": "Hacked"}, headers=member
    )
    assert r.status_code == 403


def test_nonmember_cannot_rename_board_404(client, auth):
    owner = auth("owner@x.com")
    stranger = auth("stranger@x.com")
    board = _make_board(client, owner)
    r = client.patch(
        f"/boards/{board['id']}", json={"title": "Hacked"}, headers=stranger
    )
    assert r.status_code == 404


def test_owner_can_delete_but_member_cannot(client, auth):
    owner = auth("owner@x.com")
    member = auth("member@x.com")
    board = _make_board(client, owner)
    client.post(
        f"/boards/{board['id']}/members",
        json={"email": "member@x.com"},
        headers=owner,
    )
    assert client.delete(f"/boards/{board['id']}", headers=member).status_code == 403
    assert client.delete(f"/boards/{board['id']}", headers=owner).status_code == 204


def test_inviting_members_is_owner_only(client, auth):
    owner = auth("owner@x.com")
    member = auth("member@x.com")
    auth("third@x.com")
    board = _make_board(client, owner)
    client.post(
        f"/boards/{board['id']}/members",
        json={"email": "member@x.com"},
        headers=owner,
    )
    # A non-owner member trying to invite someone → 403.
    r = client.post(
        f"/boards/{board['id']}/members",
        json={"email": "third@x.com"},
        headers=member,
    )
    assert r.status_code == 403


def test_listing_boards_returns_only_yours(client, auth):
    owner = auth("owner@x.com")
    stranger = auth("stranger@x.com")
    _make_board(client, owner, title="Owner board")
    # The stranger owns/joins nothing → empty list.
    r = client.get("/boards", headers=stranger)
    assert r.status_code == 200
    assert r.json() == []
    # The owner sees exactly their one board.
    r2 = client.get("/boards", headers=owner)
    assert [b["title"] for b in r2.json()] == ["Owner board"]
