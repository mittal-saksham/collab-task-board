# 13 — Security & performance batch (the review's deferred items)

The full-repo review (`docs/12`) fixed the correctness bugs and deferred four
items that each carried a design decision. This batch lands all four:
rate limiting, the login timing side-channel, WebSocket ticket auth, and the
N+1 eager-loading pass.

---

## 1. Rate limiting (`core/ratelimit.py`)

**The problem:** nothing throttled anything. Unlimited `POST /auth/login`
attempts against a known email (credential stuffing), unlimited signups, and —
the subtle one — every login/signup attempt runs a ~100ms bcrypt hash, so a
modest request flood pins the CPU of a single-instance deploy. `summarize`
was also unmetered, and each call costs real Anthropic API money.

**The design decision — hand-rolled vs a library:** we hand-rolled a ~40-line
**sliding-window limiter** (per-IP deque of timestamps; prune entries older
than the window; reject when the deque is full) used as a FastAPI dependency:

```python
login_limiter = RateLimiter(limit=10, window_seconds=60)

@router.post("/login", dependencies=[Depends(login_limiter)])
```

Why not `slowapi`? Three endpoints don't justify a dependency, and the
algorithm is interview-explainable in two sentences. The state is in-memory
and per-process — deliberately the **same trade-off as the WS manager**: right
for the single-instance target, and the multi-instance answer (Redis) is the
same for both. Over the limit → **429** with a `Retry-After` header.

Limits: login 10/min/IP, signup 10/min/IP, summarize 5/min/IP.

**Test-suite wrinkle:** every TestClient request comes from the same
"testclient" IP, so the auth fixture's signups would trip the limiter across
tests. `conftest.py` now calls `ratelimit.reset_all()` in the same teardown
that truncates the DB — limiter state is wiped per test like any other state.

## 2. Login timing side-channel (`core/security.py::dummy_verify`)

**The problem:** the login error body was already the same for "no such email"
and "wrong password" (good), but the response *time* wasn't: when the email
didn't exist, bcrypt never ran, so the reply came back ~100ms faster. Timing
is measurable — an attacker could enumerate which emails have accounts.

**The fix:** on the unknown-email path, verify the submitted password against
a throwaway hash (`_TIMING_DUMMY_HASH`, computed once at import) and discard
the result. Both paths now burn the same bcrypt cost. Note this only closes
the *login* channel — signup still returns a distinguishable 409 for existing
emails. That's a deliberate UX trade-off (people need to know why signup
failed), now blunted by the signup rate limit.

## 3. WebSocket ticket auth (`ws/tickets.py`, `POST /auth/ws-ticket`)

**The problem:** browsers can't set an `Authorization` header on a WebSocket
handshake, so the JWT rode in the URL (`?token=eyJ...`) — and URLs land in
server/proxy access logs. With no server-side revocation, one leaked log line
= full API access for the token's remaining lifetime (up to 60 min).

**The fix — the standard "ticket" pattern:**

1. The client (already authenticated over HTTPS) calls `POST /auth/ws-ticket`.
2. The server mints a random single-use ticket (`secrets.token_urlsafe(32)`,
   256 bits) bound to that user, valid **60 seconds**, stored in-memory.
3. The client connects `WS /ws/boards/{id}?ticket=...`. The server **redeems
   and burns** the ticket (an atomic `dict.pop`) before accepting.

A ticket in a log is worthless: consumed, expired within a minute regardless,
and never valid for REST. The frontend (`useBoardLiveUpdates`) fetches a fresh
ticket before *every* connect — including each reconnect attempt, since the
old one is spent. If the ticket fetch itself fails, the existing
backoff-retry path handles it; if it 401s, the global handler logs the user
out and the `getToken()` guard stops the loop.

Storage is per-process (same caveat and same Redis-shaped future as the WS
manager and the rate limiter — the three form one consistent story).

## 4. N+1 queries → `selectinload` batches

**The problem:** no eager loading existed anywhere. `GET /boards/{id}`
serialized `BoardDetail` by lazy-loading lists (1 query), then each list's
cards (L queries), then *per card* its assignee and labels (2·C queries):
~200 queries for a 100-card board. Members and the activity feed had the
same per-row pattern.

**The fix:** `selectinload` options on the three read paths —
board detail (`lists → cards → assignee/labels`), `list_members` (`.user`),
`list_activities` (`.actor`). SELECT-IN loading issues one extra batched
query per relationship level (`WHERE id IN (...)`), so the query count is
**constant in the number of cards**.

**The subtlety worth knowing:** `get_board_for_member` is also the authz
check behind *every* board-scoped route. Eager-loading unconditionally would
have made every card PATCH pay for loading the whole board. So the deep load
is **opt-in** (`with_contents=True`), used only by the board-detail route.

**The regression guard:** `test_security.py::test_board_detail_query_count_is_bounded`
builds a 20-card board, counts actual SELECTs via a SQLAlchemy
`before_cursor_execute` listener during the GET, and asserts ≤ 10. The lazy
version was 40+; if someone reintroduces an N+1, this fails with the
statement list in the error message.

## 5. Tests & verification

- 10 new DB-backed tests (`test_security.py`): 429s trip at the documented
  thresholds with `Retry-After`; under-limit requests unaffected; unknown-email
  login still returns the generic 401; ws-ticket requires auth; a valid ticket
  connects; **a reused ticket is rejected**; garbage tickets rejected; a
  non-member's valid ticket is rejected; and the query-count bound above.
  **50 backend + 20 frontend = 70 total.**
- Playwright end-to-end smoke re-run, now also proving **live updates flow
  through the ticket-auth WebSocket**: two browser sessions on one board, a
  card created in one appears in the other without reload.

## 6. Still deliberately out of scope

- **Signup email enumeration** (the 409) — inherent UX trade-off, mitigated by
  rate limiting.
- **JWT revocation / refresh tokens** — would need server-side state for all
  auth, not just sockets; the 60-min expiry bounds the exposure.
- **Kicking removed members' live sockets** — a removed member's open socket
  still receives events until they disconnect (REST re-checks per request).
  Fix would be a `manager.disconnect_user(board_id, user_id)` hook in the
  remove-member route; noted for later.
- **Per-user (not per-IP) rate limiting** — per-IP is coarser under NAT but
  works pre-auth, which is where the attacks are.
