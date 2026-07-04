# Project context — Collab Task Board

> **This file is the handoff doc for an AI agent picking up this project.** It's
> auto-loaded by Claude Code each session. Read it first, then the linked docs as
> needed. It is self-contained (don't rely on any machine-local memory).

---

## 1. What this is

A collaborative **Trello/Linear/Jira-style task board**, built as an **SDE
portfolio project** to demonstrate real engineering: clean data modeling, JWT
auth, real-time updates, a layered API, tests + CI. Monorepo: `backend/` (FastAPI)
+ `frontend/` (React).

**The owner is a learner** (SDE intern) improving at FastAPI/Python and
React/TypeScript. They value understanding *why*, clean minimal changes, and being
able to explain the code in a review. Early on we taught while building; later they
switched to **"auto mode"** — see Working Conventions (§6).

---

## 2. Current status

**Everything below is DONE, verified, committed, and pushed.** The build is
feature-complete.

- ✅ **Backend MVP** — auth (signup/login/JWT/`/me`), boards, lists, cards,
  fractional drag-and-drop positioning, real-time WebSockets, membership/invites.
- ✅ **LLM summarizer** (optional) — `POST /boards/{id}/summarize`, Claude via the
  `anthropic` SDK; 503 if no `ANTHROPIC_API_KEY`.
- ✅ **Frontend** — auth pages, board UI, dnd-kit drag, live updates, members.
- ✅ **Jira features G1–G4:**
  - **G1** rich cards — assignee, priority, due date, labels (M2M) + detail modal + badges (`docs/08`)
  - **G2** comments + per-board activity log; modal restyled to content+sidebar (`docs/09`)
  - **G3** issue types (task/bug/story) + story points + **display-only** WIP limits (`docs/10`)
  - **G4** client-side search/filter bar — text/assignee/label/priority/type (`docs/11`)
- ✅ **Tests + CI** — 70 tests (pytest: security (rate limits, WS tickets, N+1 guard), ordering math + rebalance, auth, board AND
  card access-control, move/PATCH semantics; vitest: filter/time helpers) on
  GitHub Actions; CI also runs `alembic upgrade head` and the frontend linter
  (`docs/LLD.md §10`).
- ✅ **Security & perf batch** (`docs/13`) — rate limiting (hand-rolled sliding
  window, per-IP, in-memory), login timing equalization (`dummy_verify`),
  single-use ~60s WebSocket tickets (`POST /auth/ws-ticket` — JWT never rides
  in a URL anymore), and `selectinload` eager loading (board detail is ~6
  queries regardless of card count, guarded by a query-count test).
- ✅ **Hardening pass from a full-repo review** (`docs/12`) — position rebalance
  fallback (was documented but never implemented!), PATCH-null 422s, global 401
  handling (no more zombie sessions), optimistic moveCard with rollback, WS
  auto-reconnect with backoff, drag off-by-one fix, mutation-error banner, dead
  code/duplication cleanup.
- ✅ **Deploy scaffolding** — `render.yaml` + `backend/Dockerfile` + `DEPLOY.md`.
- ✅ **Optimistic UI** — card delete only (create/edit deliberately deferred).

**Pending (all OPTIONAL):**
- ⏳ **Actually deploying** — the engineering is done; it needs the owner's ~15-min
  interactive Render steps (`DEPLOY.md`). **Highest-value remaining item.**
- ⏳ Optimistic **create/edit** (create needs a temp-id guard — see §7).
- ⏳ Polish — richer activity summaries ("priority High→Low"), board/list rename in
  the UI, error toasts, mobile/a11y.

---

## 3. Quickstart (run it locally)

Prereqs: Docker Desktop, Python 3.10+, Node 20+.

```bash
# 0. First time only: create the local env file (committed example has dev values)
cp .env.example .env

# 1. Postgres (runs on host port 5434 — NOT 5432, to avoid a native PG on this machine)
docker compose up -d

# 2. Backend  →  http://localhost:8000  (API + /docs)
cd backend
python -m venv .venv && source .venv/bin/activate     # first time
pip install -r requirements-dev.txt                    # prod + test deps
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend  →  http://localhost:5173  (the actual app UI)
cd frontend
npm install
npm run dev
```

- **The app UI is on `:5173`.** `:8000` is the API only (browse `:8000/docs`).
- **Demo login** (on a freshly seeded dev DB you'd create yourself):
  sign up any email; password must be ≥ 8 chars.
- Alembic migration head: **`d24c3316f954`** (G4 was frontend-only, no migration).

---

## 4. Tests & CI

```bash
# Backend (needs the Docker Postgres running; creates a throwaway taskapp_test DB)
cd backend && pip install -r requirements-dev.txt && pytest

# Frontend
cd frontend && npm test
```

CI: `.github/workflows/ci.yml` runs both on every push/PR (backend job has a
`postgres:16` service; runs migrations, pytest, lint, build, vitest). 70 tests
total. Full notes in `docs/LLD.md §10`.

---

## 5. Architecture & where things live

**Backend** (`backend/app/`) — layered:
- `models/` — SQLAlchemy 2.0 models (`Mapped`/`mapped_column`). `models/__init__.py`
  imports them all (so the registry + alembic see them). Tables: users, boards,
  memberships, lists, cards, labels, `card_labels` (assoc), comments, activities.
- `schemas/` — Pydantic v2 (the API contract; separate from models).
- `crud/` — data-access functions (these COMMIT). `crud/ordering.py` = the
  fractional-position math (pure).
- `api/` — routers. `api/access.py` = shared authz helpers (404 for non-members,
  403 for non-owners). `api/deps.py` = `get_current_user` / `CurrentUser`.
- `services/` — `llm.py` (summarizer), `activity_log.py` (records + broadcasts an
  activity, best-effort).
- `ws/manager.py` — in-memory WebSocket rooms + a sync→async broadcast bridge.
- `core/config.py` — `Settings` (env-driven). `db/session.py` — engine + `get_db`.
- `alembic/` — migrations. `tests/` — pytest (conftest + test_ordering/auth/access).

**Frontend** (`frontend/src/`):
- `lib/api.ts` — fetch wrapper (JWT, base URL, `ApiError`) + auth calls.
- `lib/boards.ts` — typed REST calls. `hooks.ts` — TanStack Query hooks +
  `useBoardMutations` (all board mutations) + `useBoardLiveUpdates` (WS).
- `lib/filters.ts` — client-side filter predicate. `lib/time.ts` — `timeAgo`/`initials`.
- `auth/` — `AuthContext` + `ProtectedRoute`. `pages/` — Login/Signup/Boards/Board.
- `components/` — `Column`, `SortableCard`, `CardItem`, `CardBadges`, `CardModal`,
  `CommentThread`, `MembersPanel`, `ActivityPanel`, `FilterBar`, `AppHeader`.
- `types.ts` — shared types mirroring the API.

---

## 6. Working conventions (HARD RULES — follow these)

1. **Don't break the existing app.** All feature work so far is strictly additive
   (nullable/defaulted columns, new routes/components). Keep it that way; verify
   regressions before declaring done.
2. **Auto mode:** build in larger *verified* batches (not tiny steps). Make+document
   sensible design calls instead of pausing — BUT do ask the owner the genuine
   board-design decisions (e.g. "WIP enforce vs display-only"). Don't pause when no
   decision is needed.
3. **Heavy docs + inline comments are a primary deliverable.** Each feature gets a
   `docs/NN-*.md`; append new concepts to `docs/CONCEPTS.md`; update HLD/README
   status. Write code that reads like the surrounding code.
4. **Commit at the end of every batch** (restore points), with a descriptive message.
5. **Git identity is PERSONAL:** repo-local config is `Saksham Mittal
   <sakshammital@gmail.com>` (NOT the work email). Remote =
   `github.com/mittal-saksham/collab-task-board` (private). Pushing needs the
   `mittal-saksham` gh account active — if a push 403s, run
   `gh auth switch --user mittal-saksham`.
6. **Verify before claiming done.** We've been driving the real UI with Playwright
   and hitting the API directly. Report faithfully (incl. what *wasn't* tested).
7. **Secrets never go in git.** `.env` is gitignored (only local dev values + a
   regenerable JWT key; no real API keys). Prod secrets live in Render's dashboard.

---

## 7. Gotchas catalogue (expensive lessons — don't relearn these)

- **Cross-module M2M relationships:** a `secondary=` many-to-many whose target is a
  string forward-ref in another module must use a **non-annotated**
  `relationship("X", secondary=…, back_populates=…)` — NOT `Mapped[list["X"]]`
  (which serializes as `None`/`uselist=False`). See `models/card.py` `labels`.
  Single-file M2M is fine annotated. (`docs/08 §2`.)
- **Adding a NOT NULL column to a populated table:** use a DB-level
  `server_default=` (e.g. `priority`, `issue_type`) so Postgres backfills existing
  rows. A Python `default=` only fires on ORM inserts and won't backfill. (`docs/08 §1`.)
- **PATCH semantics:** routes use `model_dump(exclude_unset=True)`. A key *absent* =
  "leave unchanged"; a key present as **`null`** = "clear it". The frontend must send
  literal `null` (JSON.stringify drops `undefined`) to unassign / clear a field.
  NOT NULL fields (card/list `title`, `priority`, `issue_type`) reject explicit
  null with 422 via schema validators — Pydantic v2 validators don't run on
  defaults, which is exactly why absent-vs-null can be told apart. (`docs/12 §2`.)
- **Tailwind v4 drops runtime-built class names** — only complete literal strings
  survive the build. Use a static map (see `CardBadges.tsx` `LABEL_STYLES`), never
  `` `bg-${color}-100` ``.
- **Drag vs click on a card:** `SortableCard` latches dnd-kit's `isDragging` into a
  ref so the post-drag click doesn't open the modal. A `click` targets the nearest
  common ancestor of pointerdown/up, so a cross-column drag's click never reaches a
  card's handler — the per-card ref is sufficient. (`docs/08 §5`.)
- **BoardPage renders from a local `lists` mirror** synced from the query via
  `useEffect`, so optimistic cache writes land one render tick later than textbook —
  still beats the network.
- **Optimistic create is the risky one:** a temp card has a fake (negative) id until
  the server responds; clicking/dragging it would PATCH a nonexistent id (404). Guard
  negative ids before adding optimistic create.
- **SQLAlchemy `str(url)` masks the password as `***`** — build engines from the URL
  *object*, not its string form (bit us in `tests/conftest.py`).
- **Rate limiters + WS tickets are in-memory too** (`core/ratelimit.py`,
  `ws/tickets.py`) — same single-process trade-off as the WS manager; all three
  move to Redis together if this ever scales out. Tests reset limiter state in
  the conftest teardown (same-IP TestClient requests would trip limits otherwise).
- **The WS URL carries a single-use ticket, not the JWT** — fetch a fresh one
  per connect (`getWsTicket`); a reused/expired ticket is rejected at handshake.
- **WS manager is in-memory / single-process** — fine on one instance; multi-instance
  would need Redis pub/sub. `emit()` is a no-op if the loop isn't set (e.g. in tests).
  The frontend socket auto-reconnects with backoff and refetches on reconnect
  (`useBoardLiveUpdates`); don't add a second reconnect layer on top.
- **Fractional positions rebalance when a gap is exhausted** (`crud/ordering.py`
  `gap_exhausted` + the `_rebalance_*` helpers in card/list crud), and the ORM
  orders by `(position, id)` so ties are deterministic. Concurrent same-spot
  writes can still collide (no row locks) — stable order, not corruption; a
  locking/retry scheme is a known future item. (`docs/12 §1, §6`.)

---

## 8. Where to go deep (docs index)

- `README.md` — status table + quickstart.
- `docs/HLD.md` — high-level design + architecture decision log + roadmap.
- `docs/LLD.md` — low-level design, request flows, error model, **testing (§10)**.
- `docs/01`–`07` — data model, auth, boards/lists/cards, real-time, membership,
  frontend, LLM summarizer.
- `docs/08`–`11` — the Jira groups G1–G4 (backend + frontend + the gotchas).
- `docs/CONCEPTS.md` — plain-English glossary of every concept (§1–16), with the
  "interview angle" a reviewer might probe. Append to it when teaching new concepts.
- `DEPLOY.md` — step-by-step Render deployment.

---

## 9. Suggested next steps (in priority order)

1. **Go live on Render** (`DEPLOY.md`) — owner's interactive step; biggest payoff.
2. **Optimistic edit** (safe) then **create** (with the temp-id guard).
3. Polish: richer activity summaries, board/list rename in UI, error toasts.

When you finish a batch: update the relevant `docs/*`, the README status table, and
this file's §2 if status changed; then commit.
