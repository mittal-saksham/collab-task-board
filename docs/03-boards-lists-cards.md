# 🧱 Boards, Lists & Cards (the CRUD core + drag-and-drop)

How the board's contents are created, read, and reordered — and how the
fractional-positioning algorithm shows up in real requests. Builds on
[`01-data-model.md`](01-data-model.md) (the tables) and
[`02-auth.md`](02-auth.md) (who's logged in).

---

## Resource hierarchy & routes

```
Board ── has many ──> List ── has many ──> Card
```

| Method | Path | Who | Purpose |
|--------|------|-----|---------|
| `POST` | `/boards` | any member-to-be | Create a board (you become owner) |
| `GET` | `/boards` | logged-in | List boards you can access |
| `GET` | `/boards/{id}` | board member | Board **with** its lists+cards |
| `PATCH` | `/boards/{id}` | owner | Rename board |
| `DELETE` | `/boards/{id}` | owner | Delete board (cascades) |
| `POST` | `/boards/{id}/lists` | board member | Add a column (appended to the end) |
| `PATCH` | `/lists/{id}` | board member | Rename column |
| `DELETE` | `/lists/{id}` | board member | Delete column (cascades to cards) |
| `PATCH` | `/lists/{id}/move` | board member | Reorder column |
| `POST` | `/lists/{id}/cards` | board member | Add a card (appended to the end) |
| `PATCH` | `/cards/{id}` | board member | Edit title/description |
| `DELETE` | `/cards/{id}` | board member | Delete card |
| `PATCH` | `/cards/{id}/move` | board member | **Drag-and-drop**: move/reorder |

---

## Access control: permissions come from the board

Lists and cards have **no permissions of their own** — access is decided by the
**board** they ultimately belong to. The helpers in `app/api/access.py` enforce
this:

- `require_board_member(db, board_id, user)` — is the user a member/owner?
- `require_list_access(db, list_id, user)` — resolve list → its board → member?
- `require_card_access(db, card_id, user)` — resolve card → list → board → member?

Two deliberate choices:
1. **404, not 403, for "not your board."** If you're not a member, the API says
   "not found" rather than "forbidden" — so it never reveals that a board/list/
   card *exists* to someone who shouldn't see it. (We *do* use **403** for the
   member-but-not-owner case on board edit/delete, since membership already
   confirms the board exists to them.)
2. **Owner vs. member.** Viewing and adding lists/cards needs membership; only
   the **owner** (`Board.owner_id`) can rename or delete the board.

> 🧠 **Concept — authorization via the parent resource:** rather than storing
> permissions on every row, child resources inherit access from a parent. It
> keeps the model simple and the checks in one place (`access.py`).

---

## Creating a board is a 2-row transaction

`create_board` inserts the board **and** the owner's membership row in one commit:

```python
board = Board(title=title, owner_id=owner_id)
db.add(board)
db.flush()          # sends the INSERT, so board.id is now known...
db.add(Membership(board_id=board.id, user_id=owner_id, role="owner"))
db.commit()         # ...both rows saved together (atomic)
```

> 🧠 **`flush()` vs `commit()`:** `flush()` sends pending SQL to the DB (so
> auto-generated ids like `board.id` become available) but stays inside the open
> transaction; `commit()` makes it permanent. Doing both inserts before a single
> `commit()` means they succeed or fail *together* — you can't end up with a
> board that has no owner-membership.

---

## The full-board read (nested response)

`GET /boards/{id}` returns a `BoardDetail`, which composes smaller schemas:

```
BoardDetail
 ├─ id, title, owner_id, created_at
 └─ lists: [ ListWithCards
              ├─ id, board_id, title, position, created_at
              └─ cards: [ CardRead, ... ]   # ordered by position
            ]
```

The ordering is automatic: the ORM relationships declare
`order_by="List.position"` and `order_by="Card.position"`, so the lists and cards
come back already sorted. One request gives the frontend everything to render a
board.

> 🧠 **Concept — nested/compositional response models:** Pydantic schemas can
> contain other schemas. `BoardDetail` embeds `ListWithCards`, which embeds
> `CardRead`. FastAPI serializes the whole tree and (because each is a
> `response_model`) still strips anything not declared.

---

## Positioning in action (the interview centerpiece)

Every list and card has a `float position`. Two operations use it:

### Append on create
New lists/cards go to the **end**: `position = max(sibling positions) + 1024`.
That's why our three cards came out `1024, 2048, 3072`.

### Move (`PATCH /cards/{id}/move`)
Body: `{ "list_id": <target column>, "after_id": <card to drop behind | null> }`.
The server computes the new position from the two neighbours at the drop spot:

```python
# in app/crud/ordering.py
def position_between(prev, next):
    if prev is None and next is None: return 1024      # empty target
    if prev is None:                  return next / 2  # drop at FRONT
    if next is None:                  return prev + 1024  # drop at BACK
    return (prev + next) / 2                            # midpoint
```

**Worked example from our verification run:**
- Start — To Do: `A(1024) B(2048) C(3072)`, Doing: empty.
- **Move A → Doing, front** (`after_id=null`): Doing is empty → `position_between(None, None) = 1024`. A is now in Doing at `1024`, and crucially its `list_id` changed — that's the cross-column drag.
- **Move C → front of To Do** (`after_id=null`): front, next neighbour is B at `2048` → `2048 / 2 = 1024`. To Do becomes `C(1024) B(2048)` — **B was never touched**.

That "B untouched" is the whole point: a move is **one row's `UPDATE`**, no
resequencing. See [`01-data-model.md`](01-data-model.md#card--list-ordering-fractional-float-positions)
for the rebalance fallback when a gap eventually gets too small.

### Guard rails on move
- `after_id` must reference an item **in the target list/board** (else `400`).
- You can't place an item **after itself** (`400`).
- A card can't move to a **different board** (`400`).

---

## File map

| File | Role |
|------|------|
| `app/schemas/board.py`,`list.py`,`card.py` | request/response shapes (incl. nested `BoardDetail`) |
| `app/crud/board.py` | create(+owner membership), list-mine, access query, update, delete |
| `app/crud/list.py` | create(append), update, delete, **move** |
| `app/crud/card.py` | create(append), update, delete, **move** |
| `app/crud/ordering.py` | the pure positioning math |
| `app/api/access.py` | membership/owner authorization helpers |
| `app/api/boards.py`,`lists.py`,`cards.py` | the routers |

➡️ Next: **real-time sync** — broadcasting these create/move/delete events over
WebSockets so collaborators see them live.
