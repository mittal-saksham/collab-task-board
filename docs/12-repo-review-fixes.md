# 12 — Repo review: hardening fixes + cleanup pass

A full-repo review (four passes: backend correctness, backend security, frontend,
infra/tests/docs) surfaced a cluster of real bugs — mostly in **failure handling**:
the app behaved well on the happy path and silently lied to the user the moment
anything failed. This batch fixes the highest-impact items and removes the dead /
duplicated code the review turned up.

---

## 1. The rebalance fallback actually exists now (backend)

**The bug:** the docs (LLD §6, HLD, and `ordering.py`'s own docstring) described a
rebalance step for when fractional positions exhaust float precision — but no such
code existed. After ~50 midpoint insertions into the same gap, `(prev + next) / 2`
returns one of its endpoints (float64 runs out of bits), so two cards get
**identical** positions. With `order_by="Card.position"` alone, ties render in
arbitrary, load-dependent order — the board silently corrupts and can't self-heal.

**The fix** (`crud/ordering.py`, `crud/card.py`, `crud/list.py`):

- `gap_exhausted(prev, next)` — true when the gap at the drop spot is ≤ `MIN_GAP`
  (1e-6). Edges (`None` on either side) are never exhausted — inserting at the
  front/back always extends the range instead of subdividing it.
- `rebalanced_positions(n)` — fresh, evenly-spaced positions (`GAP, 2·GAP, …`).
- `move_card` / `move_list` check the gap *before* placing: if it's exhausted,
  renumber that ONE list's siblings (ordered by `(position, id)`), `flush()`, then
  re-read the neighbours and place normally. Cost: `O(k)` for one list, and only
  in the rare exhausted case — every normal move is still a single-row update.

**Plus a determinism guard:** the ORM relationships now order by
`(position, id)` instead of `position` alone, so even if two rows *did* collide
(e.g. via a concurrent-write race — see §6), their order is stable rather than
whatever the query planner felt like.

**Test that proves it:** `test_cards.py::test_repeated_moves_into_same_gap_stay_ordered`
drags a card into the same slot **60 times** (past the ~50-iteration precision
cliff) through the real API and asserts order and distinctness. The old pure-math
test deliberately stopped at 20 iterations — below the failure threshold.

## 2. Explicit `null` on NOT NULL fields → 422, not 500 (backend)

Our PATCH convention: an **absent** key = "leave unchanged", a key present as
`null` = "clear it" (`model_dump(exclude_unset=True)`). But `title`, `priority`,
and `issue_type` are NOT NULL columns — "clear it" is meaningless, and an explicit
`{"title": null}` sailed through `Optional[str]`, hit `setattr`, and blew up as an
unhandled `IntegrityError` → 500.

Fix: `field_validator`s on `CardUpdate` / `ListUpdate` that reject `None` for
those fields. The subtlety that makes this work: **Pydantic v2 validators don't
run on defaults**, so an *absent* field (default `None`) skips the validator,
while an explicitly-sent `null` hits it → clean 422. Nullable fields
(`assignee_id`, `story_points`, `due_date`, `wip_limit`, `description`) keep the
clear-with-null behavior — there's a regression test for both directions.

## 3. Expired-token handling: no more zombie sessions (frontend)

**The bug:** `AuthContext` validated the token once on mount, and nothing handled
401s afterwards. When the 60-minute JWT expired mid-session, the user stayed
"logged in" while every write silently failed — you could drag cards and edit
titles for ten minutes and lose all of it.

**The fix** (`lib/api.ts` + `AuthContext`):

- `apiFetch` now intercepts any 401 *that had a token attached*: it clears the
  token and fires a callback `AuthContext` registers. `setUser(null)` →
  `ProtectedRoute` redirects to login. One place, covers every query and mutation.
- The startup `/auth/me` check no longer wipes the token on **network errors or
  5xx** — only a real 401 invalidates it. This mattered for the planned Render
  deploy: the free-tier backend cold-starts, and the old
  `.catch(() => setToken(null))` would have logged the user out on every wake.
- The `QueryClient` no longer retries 4xx responses (they're deterministic —
  retrying an expired-token 401 or a nonexistent-board 404 three times just
  delays the error state).

## 4. Drag-and-drop is now failure-proof and preview-accurate (frontend)

Three related fixes in the move path:

- **`moveCard` is a real optimistic mutation** (same shape as `deleteCard`):
  `onMutate` cancels in-flight board refetches and writes the move into the query
  cache; `onError` rolls back; `onSettled` re-syncs with the server. Previously it
  was fire-and-forget with `onSuccess`-only invalidation — a failed PATCH left the
  card visually moved **forever** with no feedback. `cancelQueries` also closes a
  race: a refetch triggered *before* the drag (say, by a teammate's WS event)
  used to resolve with pre-drag data and visibly snap the card back.
- **The downward off-by-one:** "insert before the card you dropped on" is only
  correct for upward and cross-list drags. Dragging *down* within a list, the
  sortable preview shows the card sliding in **below** the one it's over — so the
  code now inserts after it in that case. Before, the card landed one slot above
  where the preview showed, and the wrong `after_id` was persisted. Verified
  end-to-end with a Playwright drag (`[Alpha,Bravo,Charlie]` → drag Alpha over
  Charlie → `[Bravo,Charlie,Alpha]`, stable across reload).
- **Mid-drag crash guard:** the optimistic splice used a non-null assertion on
  "the target list is still there"; if a teammate deleted that list mid-drag it
  threw and (with no error boundary) blanked the whole app. Now it bails to the
  previous state and lets the re-sync sort it out.

Failed writes are no longer invisible: the board page shows a banner ("that
change didn't save — the board has been restored") whenever any board mutation
errors. Each mutation resets its error the next time it runs, so the banner
clears itself.

## 5. The WebSocket reconnects (frontend)

`useBoardLiveUpdates` opened one socket and registered only `onmessage`. Any drop
— backend redeploy, laptop sleep, a proxy idle-timeout — and live updates died
silently for the rest of the session. Now: `onclose` schedules a reconnect with
exponential backoff (1s → 2s → 4s → … capped at 30s), `onopen` resets the backoff
**and refetches everything** (events may have been missed while disconnected),
and unmount sets a flag so cleanup doesn't trigger a zombie reconnect loop.

## 6. What we deliberately did NOT fix (known limitations)

Recorded so nobody mistakes silence for ignorance:

- **Concurrent-write races on positions** — two clients computing the same
  midpoint simultaneously can still collide (no `SELECT … FOR UPDATE`, no unique
  constraint). The id tiebreak makes the result *stable* rather than corrupt, and
  single-user/small-team use never hits it. Proper fix = row locks or a retry
  loop; noted for the roadmap.
- **Rate limiting / login timing side-channel / signup email enumeration** —
  real security hygiene items from the review, deferred as a follow-up batch.
- **JWT in the WS query string** — browsers can't set headers on WebSocket
  connects; the clean fix is a short-lived one-time ticket endpoint. Deferred.
- **N+1 queries on board load** — no `selectinload` anywhere; a 100-card board
  is ~200 queries. Painless to add later; irrelevant at demo scale.
- **WS membership is checked only at connect** — a member removed mid-session
  keeps receiving events until they close the tab (REST re-checks per request).

## 7. Cleanup pass ("AI slop" removal)

A dedicated audit for dead/unnecessary code found and we removed:

| What | Where | Why it was safe |
|---|---|---|
| `moveList` mutation + API call | `hooks.ts`, `lib/boards.ts` | No UI ever called it (columns aren't draggable). The *backend* endpoint stays — documented API surface, and list-drag is a plausible future feature. |
| Vite scaffold leftovers | `App.css` (185 lines), `src/assets/*` | Never imported anywhere. |
| Duplicated `PRIORITIES` array | `CardModal`, `FilterBar` | Now exported once from `CardBadges` (which both already imported). |
| Private `initials()` re-copy | `CardBadges` | `lib/time.ts` already exports (and unit-tests) it. |
| Unreachable `??` fallbacks | `CardBadges` | `issue_type`/`priority` are backend-validated `Literal` enums — no card can carry an unknown value. (Label colors keep their fallback: the raw API accepts any string there.) |
| 4 inlined authz check blocks | `api/boards.py` | `access.require_board_member/owner` existed for exactly this; every other router already used them. |
| `_board_id_of` ×3, `_short`/`_truncate` ×2 | cards/labels/comments routers | Consolidated as `access.board_id_of_card` and `activity_log.short`. |

Two review findings fixed opportunistically along the way:
`activity_log.log` now `logger.exception`s what it swallows (a permanent bug
there used to kill the activity feed with zero operator signal), and the
summarize route no longer reflects raw Anthropic exception strings to clients.

## 8. Tests & CI after this batch

- **60 tests** (was 47): 40 backend + 20 frontend. New `backend/tests/test_cards.py`
  covers the rebalance under sustained same-gap moves, move-to-front/back,
  cross-list moves, PATCH null semantics both ways, **card-level access control**
  (the old suite only checked authz on `/boards/*` — cards/lists/comments were
  exactly where a forgotten check would ship unnoticed), and the cross-board
  move rejection.
- **CI now runs `alembic upgrade head`** against the service Postgres before
  pytest. The tests build their schema via `create_all`, so migration/model
  drift used to pass CI green and explode for the first time during a Render
  deploy. Now a broken migration chain fails the build.
- **CI now runs the frontend linter** (`npm run lint` was defined in
  package.json but never executed anywhere).
- `.env.example` now defaults to port **5434**, matching README/CLAUDE.md — the
  committed 5432 would have recreated the exact port-collision the 5434 choice
  exists to avoid.
