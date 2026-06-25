# 👥 Membership & Invites

How a board becomes multi-user: the owner invites existing users by email, and
those members gain access to everything on the board.

---

## How invites work (MVP choice)

You invite **an existing user, by email**. The server looks up that email; if a
user exists, it adds a `memberships` row linking them to the board. No emails are
sent and no invite tokens/links are created — the simplest path to collaboration.

> The alternative (a shareable invite *link*) would let people who don't have an
> account yet join, but needs token generation, expiry, and a join flow. We
> deferred it.

---

## Routes

| Method | Path | Who | Result |
|--------|------|-----|--------|
| `GET` | `/boards/{id}/members` | any member | List members (email + role) |
| `POST` | `/boards/{id}/members` | **owner** | Invite a user by email |
| `DELETE` | `/boards/{id}/members/{user_id}` | **owner** | Remove a member |

**Authorization** is enforced by `access.require_board_owner(...)` for
invite/remove (404 if you can't see the board, 403 if you're a member but not the
owner). Listing only needs `require_board_member`.

**Validation handled:**
- invite an email with no account → `404 No user with that email`
- invite someone already a member → `409` (also guarded by the DB unique
  constraint on `(board_id, user_id)`)
- remove the owner → `400 Cannot remove the board owner`
- remove someone who isn't a member → `404`

---

## Why access "just works" after an invite

All board access flows through one query — `get_board_for_member`, which joins
`boards` to `memberships`. So the moment an invite inserts a membership row, that
user passes the access check on **every** board/list/card/WebSocket endpoint. No
per-resource permission wiring needed — that's the payoff of deciding access at
the board level (see [`03-boards-lists-cards.md`](03-boards-lists-cards.md)).

We verified the full transition: a user gets `404` on the board before the
invite, `200` after, and `404` again after removal.

---

## Real-time

Invites/removals broadcast `member.added` / `member.removed` events to the
board's watchers, so a member list open in another browser updates live.

---

## File map

| File | Role |
|------|------|
| `app/schemas/member.py` | `MemberInvite` (email), `MemberRead` (user_id, email, role) |
| `app/crud/membership.py` | get / add / list / remove membership rows |
| `app/api/access.py` | `require_board_owner` (owner-only gate) |
| `app/api/members.py` | the three member routes |

➡️ The backend MVP is now complete. Next: the **React + TypeScript frontend** that
consumes all of these APIs and the WebSocket feed.
