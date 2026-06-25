# 📚 Concepts Reference

A living glossary for this project. Every time we introduce a new concept while
building, it gets documented here in plain English — with **why it matters**, a
**real example from our code**, and (where useful) the **interview angle** an
SDE reviewer might probe.

> How to use this file: skim the Table of Contents, jump to a concept, and read
> the "Plain English" line first. The deeper notes are there when you want them.

---

## Table of Contents

1. [Project & Architecture](#1-project--architecture)
   - [Monorepo](#monorepo)
   - [Layered architecture: models vs schemas vs crud vs api](#layered-architecture-models-vs-schemas-vs-crud-vs-api)
2. [Configuration & Secrets](#2-configuration--secrets)
   - [Environment variables & 12-factor config](#environment-variables--12-factor-config)
   - [`.env` vs `.env.example`](#env-vs-envexample)
   - [pydantic-settings & the `BaseSettings` v2 gotcha](#pydantic-settings--the-basesettings-v2-gotcha)
   - [`@property` (computed attribute)](#property-computed-attribute)
3. [Database & ORM](#3-database--orm)
   - [ORM (Object-Relational Mapper)](#orm-object-relational-mapper)
   - [Engine (connection pool)](#engine-connection-pool)
   - [Session](#session)
   - [SQLAlchemy 2.0 style vs legacy](#sqlalchemy-20-style-vs-legacy)
   - [Declarative Base](#declarative-base)
   - [psycopg v3 driver & the database URL](#psycopg-v3-driver--the-database-url)
   - [Sync vs Async (our migration plan)](#sync-vs-async-our-migration-plan)
   - [Migrations (Alembic)](#migrations-alembic)
4. [FastAPI / Web Layer](#4-fastapi--web-layer)
   - [Dependency Injection (`Depends`)](#dependency-injection-depends)
   - [The `yield` dependency (setup/teardown) pattern](#the-yield-dependency-setupteardown-pattern)
   - [Auto-generated docs (`/docs`)](#auto-generated-docs-docs)
   - [A health check that proves DB connectivity](#a-health-check-that-proves-db-connectivity)
5. [Docker & Infrastructure](#5-docker--infrastructure)
   - [Image vs Container](#image-vs-container)
   - [docker-compose](#docker-compose)
   - [Port publishing (`host:container`)](#port-publishing-hostcontainer)
   - [`localhost` binding precedence (the bug we hit)](#localhost-binding-precedence-the-bug-we-hit)
   - [Named volumes (data persistence)](#named-volumes-data-persistence)
   - [Healthcheck](#healthcheck)
6. [Debugging Lessons](#6-debugging-lessons)
   - [How to read a Python traceback](#how-to-read-a-python-traceback)
7. [Relationships, Auth & Migrations (Batch 1)](#7-relationships-auth--migrations-batch-1)
   - [ORM relationships](#orm-relationships)
   - [Foreign key](#foreign-key)
   - [Unique constraint](#unique-constraint)
   - [Association (join) table — many-to-many](#association-join-table--many-to-many)
   - [Forward references & TYPE_CHECKING](#forward-references--type_checking)
   - [Fractional indexing (ordering)](#fractional-indexing-ordering)
   - [Hashing & salt (bcrypt)](#hashing--salt-bcrypt)
   - [JWT (JSON Web Token)](#jwt-json-web-token)
   - [OAuth2 password flow & Bearer token](#oauth2-password-flow--bearer-token)
   - [Pydantic schema validation](#pydantic-schema-validation)
   - [APIRouter](#apirouter)
8. [Boards, Lists & Cards (Batch 2)](#8-boards-lists--cards-batch-2)
   - [Authorization via the parent resource](#authorization-via-the-parent-resource)
   - [404 vs 403 (don't leak existence)](#404-vs-403-dont-leak-existence)
   - [flush() vs commit() (atomic writes)](#flush-vs-commit-atomic-writes)
   - [SQL JOIN in SQLAlchemy](#sql-join-in-sqlalchemy)
   - [Nested response models](#nested-response-models)
9. [Real-time / WebSockets (Batch 3)](#9-real-time--websockets-batch-3)
   - [WebSocket](#websocket)
   - [Connection rooms](#connection-rooms)
   - [Sync → async bridge](#sync--async-bridge)
   - [Query-param WebSocket auth](#query-param-websocket-auth)
   - [Delta events vs snapshots](#delta-events-vs-snapshots)
   - [Lifespan (startup/shutdown)](#lifespan-startupshutdown)
10. [Membership & Invites (Batch 4)](#10-membership--invites-batch-4)
    - [Owner-only authorization](#owner-only-authorization)
    - [Invite an existing user by email](#invite-an-existing-user-by-email)
11. [LLM Summarizer (Batch 6)](#11-llm-summarizer-batch-6)
    - [LLM API call (single request)](#llm-api-call-single-request)
    - [Optional, isolated feature (config flag)](#optional-isolated-feature-config-flag)
    - [Graceful degradation](#graceful-degradation)
12. [Rich Cards / Jira-style fields (G1)](#12-rich-cards--jira-style-fields-g1)
    - [Many-to-many via an association table](#many-to-many-m2m-via-an-association-table)
    - [server_default vs Python default](#server_default-vs-python-default-backfilling-a-not-null-column)
    - [Partial update with exclude_unset](#partial-update-with-exclude_unset--the-null-vs-absent-distinction)
    - [Tailwind v4: only literal class names survive](#tailwind-v4-only-literal-class-names-survive-the-build)
    - [Drag vs click (latching a gesture)](#drag-vs-click-on-the-same-element-latching-a-gesture)
    - [Remount on reparent (React keys are per-parent)](#remount-on-reparent-why-react-keys-are-per-parent)

> 📄 Deeper dives live in [`01-data-model.md`](01-data-model.md),
> [`02-auth.md`](02-auth.md), [`03-boards-lists-cards.md`](03-boards-lists-cards.md),
> and [`04-realtime-websockets.md`](04-realtime-websockets.md). This glossary is
> the quick lookup.

---

## 1. Project & Architecture

### Monorepo

**Plain English:** One Git repository that holds *both* the backend and the
frontend (and the infra files), instead of two separate repos.

**Why it matters:** For a portfolio project, a reviewer clones one repo and sees
the whole system — API, UI, Docker — together. Less friction, easier to keep
frontend/backend changes in sync.

**In our code:** the repo root contains `backend/`, (later) `frontend/`,
`docker-compose.yml`, and `README.md`.

**Alternative & tradeoff:** *Polyrepo* (separate repos) only pays off at large
org scale, where teams deploy services on independent pipelines. Here it would
just add overhead.

---

### Layered architecture: models vs schemas vs crud vs api

**Plain English:** We split backend code by *responsibility* into separate
folders so each file does one job.

| Layer | Folder | Job |
|-------|--------|-----|
| **Models** | `app/models/` | How data is shaped *in the database* (tables, columns, foreign keys). SQLAlchemy. |
| **Schemas** | `app/schemas/` | What the API *accepts and returns* (the public contract). Pydantic. |
| **CRUD** | `app/crud/` | Functions that *read/write the database* ("data-access layer"). |
| **API** | `app/api/` | HTTP route handlers — status codes, auth checks; stays thin. |

**Why it matters — the key insight:** **Models ≠ Schemas, on purpose.** The DB
stores things the API must never return (e.g. a user's `password_hash`). Keeping
them separate is your "don't leak internal data" boundary. Keeping CRUD separate
from API means database logic is testable without spinning up HTTP, and routes
stay readable.

**Interview angle:** "Why separate your ORM models from your Pydantic schemas?"
→ Different reasons to change, plus a security boundary (never serialize a model
directly if it contains secrets).

---

## 2. Configuration & Secrets

### Environment variables & 12-factor config

**Plain English:** Read configuration (DB URL, secrets) from the *environment*
rather than hard-coding it in the source.

**Why it matters:** The same code runs on your laptop, in CI, and in production
just by changing env vars — no code edits, and secrets never get committed. This
is one of the "12-factor app" principles.

**In our code:** `app/core/config.py` loads values via `pydantic-settings`.

---

### `.env` vs `.env.example`

**Plain English:** Two files that look similar but serve opposite purposes.

- **`.env`** — the *real* values for your machine. **Gitignored** (never
  committed) because it can contain secrets.
- **`.env.example`** — a *template* listing which variables are needed, with safe
  placeholder values. **Committed**, so a new developer knows what to fill in.

**Why it matters:** Secrets stay out of version control, but newcomers still know
exactly what configuration the app expects.

**Real example from this project:** our `.env` sets `POSTGRES_PORT=5434` (because
this machine already had Postgres on 5432), while `.env.example` keeps the
conventional `5432`. That divergence is *correct* — `.env` reflects local
reality; `.env.example` is the clean default for anyone cloning the repo.

---

### pydantic-settings & the `BaseSettings` v2 gotcha

**Plain English:** `pydantic-settings` is a library that turns environment
variables into a typed Python object, validating types as it goes.

**Why it matters:** Instead of `os.environ["POSTGRES_PORT"]` (a string you must
parse and validate yourself), you declare `postgres_port: int` and get a
validated integer — or a clear error at startup if it's missing/invalid.

**⚠️ The gotcha:** In Pydantic **v1**, `BaseSettings` lived in `pydantic`. In
Pydantic **v2** it moved to a separate package:
```python
# v2 (correct):
from pydantic_settings import BaseSettings, SettingsConfigDict
# v1 (will fail under v2):
from pydantic import BaseSettings   # ImportError
```

**In our code (`app/core/config.py`):**
```python
class Settings(BaseSettings):
    postgres_user: str          # matched (case-insensitively) to POSTGRES_USER
    postgres_port: int = 5432   # default if the env var is absent
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")
```
Each attribute name maps to an env var of the same name. `extra="ignore"` means
unrelated keys in `.env` won't cause an error.

---

### `@property` (computed attribute)

**Plain English:** A method you access like an attribute (no parentheses). It
*computes* a value on demand instead of storing it.

**Syntax to reuse:**
```python
class Settings:
    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg://{self.postgres_user}:..."
# usage: settings.database_url   <-- no ()
```

**Why we used it:** We store the connection *parts* (`user`, `password`,
`host`, `port`, `db`) and assemble the full URL on demand. No duplicated
connection string to keep in sync.

---

## 3. Database & ORM

### ORM (Object-Relational Mapper)

**Plain English:** A library that lets you work with database rows as Python
objects, instead of writing raw SQL strings by hand.

**Why it matters:** You write `user.email` instead of parsing query results; the
ORM generates the SQL. It also helps prevent SQL-injection and makes
relationships (user → boards → cards) natural to express. Our ORM is
**SQLAlchemy**.

**Tradeoff:** ORMs add a learning curve and can hide expensive queries. Knowing
the SQL it generates (we'll use `echo=True` to *see* it) is what separates
beginners from people who can debug performance.

---

### Engine (connection pool)

**Plain English:** SQLAlchemy's manager of a *pool* of reusable connections to
Postgres. Created **once** for the whole app's lifetime.

**Why it matters:** Opening a brand-new DB connection per request is slow. A pool
keeps a handful open and hands them out, returning each when the request is done.

**In our code (`app/db/session.py`):**
```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
```
`pool_pre_ping=True` quietly checks a pooled connection is still alive before
using it (avoids "server closed the connection unexpectedly" errors).

---

### Session

**Plain English:** Your workspace for one *unit of work* — usually one HTTP
request. You add/query objects in a Session, then `commit()` to save.

**Why it matters:** Each request gets its **own** Session so concurrent users
don't interfere with each other's pending changes. The Session also tracks which
objects changed, batching the writes.

**In our code:** `SessionLocal = sessionmaker(bind=engine, autoflush=False,
autocommit=False)`. `autocommit=False` means nothing is saved until *you*
explicitly call `commit()` — giving you control over transactions.

---

### SQLAlchemy 2.0 style vs legacy

**Plain English:** SQLAlchemy has two ways to write code. We use the modern
**2.0** style everywhere.

| Concern | 2.0 style (use this) | Legacy (avoid) |
|---------|----------------------|----------------|
| Define models | `Mapped[int]` + `mapped_column()` | `Column(Integer)` |
| Query | `session.execute(select(User))` | `session.query(User)` |

**Why it matters for *us* specifically:** the 2.0 `select()` construction is
**byte-for-byte identical** between sync and async code. Since we plan to start
sync and later switch to async, writing 2.0 style now means the switch touches
very few files. Writing legacy `.query()` would force a rewrite later.

---

### Declarative Base

**Plain English:** A shared base class that all your ORM models inherit from.
SQLAlchemy uses it to keep a *registry* of every table.

**Why it matters:** That registry is how tools like Alembic "see" your whole
schema to generate migrations.

**In our code (`app/db/base.py`):**
```python
class Base(DeclarativeBase):   # 2.0 style (not the old declarative_base() function)
    pass
```
Soon: `class User(Base): ...`, `class Board(Base): ...`, etc.

---

### psycopg v3 driver & the database URL

**Plain English:** A *driver* is the low-level library that actually speaks the
Postgres wire protocol. SQLAlchemy is the ORM on top; psycopg is the driver
underneath. We use **psycopg version 3**.

**Why this choice matters:** psycopg 3 speaks **both** sync and async. So when we
switch to async later, we won't even change the driver — only the engine/session
setup. (The older `psycopg2` is sync-only; you'd have to swap to `asyncpg`.)

**The connection URL (built in `config.py`):**
```
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
            ^^^^^^^ selects the psycopg v3 driver
```

---

### Sync vs Async (our migration plan)

**Plain English:**
- **Sync (synchronous):** code runs one line at a time; a DB call *blocks* until
  it returns. Simple to read and debug.
- **Async (asynchronous):** code can `await` a slow operation and let the server
  do other work meanwhile. More throughput under load, but more complex.

**Our decision:** start **sync** to learn the ORM clearly, then switch to async
later (it pairs naturally with WebSockets and FastAPI's async style).

**The honest cost of switching (flagged early):** even with 2.0 style, every CRUD
function gains `async`/`await`. And the real async footgun is that
**lazy-loaded relationships don't work** under async — you must *eager-load* with
`selectinload(...)`. We'll design our relationships with that in mind.

---

### Migrations (Alembic)

**Plain English:** A migration is a *versioned script* describing a change to your
database structure (e.g. "create the `cards` table", "add a `position` column").
You run them in order to bring any database to the exact same schema.

**Why it matters:** It's "git for your database shape." Instead of hand-editing
the DB (which teammates and your production server would never know about), the
change is a script committed to the repo. **Alembic** is SQLAlchemy's migration
tool — now wired up in `backend/alembic/`. See the
[Migrations section of the data-model doc](01-data-model.md#migrations-how-these-tables-got-created)
for the autogenerate workflow.

---

## 4. FastAPI / Web Layer

### Dependency Injection (`Depends`)

**Plain English:** FastAPI's way of saying "before this route runs, build this
thing for me and pass it in."

**Why it matters:** Routes declare *what they need* (a DB session, the current
user) and FastAPI *provides* it. This keeps routes clean and makes them trivial
to test — in a test you can swap the real dependency for a fake one.

**In our code (`app/main.py`):**
```python
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
```
We never call `SessionLocal()` inside the function — FastAPI calls `get_db` for
us and injects the result as `db`.

**Interview angle:** "Why `Depends(get_db)` instead of creating a session inside
the handler?" → Centralizes setup/teardown, guarantees cleanup, and makes the
route testable by overriding the dependency.

---

### The `yield` dependency (setup/teardown) pattern

**Plain English:** A dependency that *sets up* a resource, hands it over with
`yield`, then *tears it down* afterward — even if the route raised an error.

**Syntax to reuse (memorize this shape):**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db          # hand the resource to the route
    finally:
        db.close()        # ALWAYS runs after the response — even on error
```

**Why it matters:** It's the canonical FastAPI idiom for anything needing
cleanup (DB sessions, file handles, network clients). The `finally` block is what
guarantees the connection returns to the pool instead of leaking.

---

### Auto-generated docs (`/docs`)

**Plain English:** FastAPI reads your route signatures and type hints and builds
an interactive API documentation page automatically at `/docs`.

**Why it matters:** Zero extra work — you get a live page to try endpoints,
generated from the same type hints that validate your data. Great for demos and
for a reviewer exploring your API.

---

### A health check that proves DB connectivity

**Plain English:** Our `/health` doesn't just return "ok" — it runs a real
`SELECT 1` against Postgres first.

**Why it matters:** A *static* health check can report green while your DB
credentials are wrong — you'd never know until a real feature breaks. Making the
endpoint actually touch the database means "green" *proves* the whole chain
works. This was our verification that Step 3 (the skeleton) was correct.

---

## 5. Docker & Infrastructure

### Image vs Container

**Plain English:**
- An **image** is a frozen template (e.g. `postgres:16`) — like a class.
- A **container** is a running instance of an image — like an object.

**In our code:** `docker-compose.yml` says `image: postgres:16`; running
`docker compose up` creates the `taskapp_db` *container* from it.

---

### docker-compose

**Plain English:** A tool to define and run multi-container setups from one YAML
file, so a whole local environment starts with `docker compose up`.

**Why it matters:** No installing Postgres on your laptop; anyone who clones the
repo gets an identical database with one command. Reproducibility is a strong
DevOps signal on a portfolio.

**In our code:** `docker-compose.yml` defines the `db` service (Postgres), its
credentials (from `.env`), its published port, a volume, and a healthcheck.

---

### Port publishing (`host:container`)

**Plain English:** `"5434:5432"` maps a port on your Mac (the host) to a port
inside the container.

```
"5434:5432"
  │     └── container port — Postgres ALWAYS listens on 5432 inside
  └──────── host port — what YOU connect to from your machine
```

**Why it matters:** The container's internal port is fixed (5432 for Postgres),
but you can choose any free host port to reach it. We used this to dodge a
conflict — see the next entry.

---

### `localhost` binding precedence (the bug we hit)

**Plain English:** When two programs "listen" on the same port number but on
different addresses, the OS sends a connection to the **more specific** address.

**The real bug (our war story):** This machine already had a *native* Postgres
listening on the specific addresses `127.0.0.1:5432` and `[::1]:5432`. Docker's
forwarder listened on the *wildcard* `*:5432` (all addresses). When our backend
connected to `localhost:5432`, the OS preferred the specific `127.0.0.1` listener
— the **native** Postgres — which had no `taskapp` role. Result:
`FATAL: role "taskapp" does not exist`, even though our container was perfect.

**Why no "port already allocated" error?** A specific-address bind
(`127.0.0.1`) and a wildcard bind (`0.0.0.0`/`*`) can *coexist* — they're not
considered the same socket — so Docker started without complaint.

**The fix:** publish our container on a *free* host port (`5434`) and point the
app there. Lesson: **on a shared dev machine, never assume a "standard" port is
free** — check with `lsof -nP -iTCP:<port> -sTCP:LISTEN`.

---

### Named volumes (data persistence)

**Plain English:** A named volume is Docker-managed disk storage that **survives**
container restarts and recreation.

**Why it matters:** Without it, `docker compose down` (or recreating the
container, like we did to change the port) would wipe your database. With it, your
data persists.

**In our code:**
```yaml
volumes:
  - taskapp_pgdata:/var/lib/postgresql/data   # Postgres stores its data here
```
This is exactly why our `taskapp` role/database survived when we recreated the
container on the new port.

---

### Healthcheck

**Plain English:** A command Docker runs *inside* the container to decide whether
the service is truly ready (not just "started").

**Why it matters:** `docker compose up --wait` blocks until the healthcheck
passes, so we don't try to connect before Postgres is actually accepting queries.

**In our code:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
```
`pg_isready` is a Postgres tool that returns success once the server can accept
connections.

---

## 6. Debugging Lessons

### How to read a Python traceback

**The skill:** A traceback is printed *outermost-call-first*, but the **root
cause is usually at the very bottom** (the innermost exception) — *or*, when you
see `The above exception was the direct cause of the following exception`, the
**first/top** exception is the original trigger and everything after is wrapping.

**What we actually did:** Out of a 3,000-line error dump, the one line that
mattered was:
```
psycopg.OperationalError: connection failed: ... FATAL: role "taskapp" does not exist
```
Everything below it was just the call stack unwinding through SQLAlchemy →
FastAPI → uvicorn. **Find the real error message first; ignore the framework
frames until you have it.** Then form a hypothesis and *verify it with a command*
(we ran `lsof` and `docker exec ... psql`) instead of guessing.

---

## 7. Relationships, Auth & Migrations (Batch 1)

### ORM relationships

**Plain English:** `relationship()` is a Python-side link between models that lets
you navigate related rows as attributes — `board.owner`, `list.cards` — instead
of writing JOINs by hand. It is *not* a database column.

**Key options we use:**
- **`back_populates`** — names the matching attribute on the other side so both
  stay in sync in memory (`card.list` ↔ `list.cards`).
- **`cascade="all, delete-orphan"`** — deleting a parent deletes its children
  (delete a board → its lists/cards go too).
- **`order_by="Card.position"`** — load children already sorted.

**Interview angle:** "Is `relationship()` a column?" → No; it's an ORM convenience
backed by the foreign key. The FK is what the DB stores.

---

### Foreign key

**Plain English:** A column whose value must match a primary key in another table
(`Board.owner_id` → `users.id`). The database enforces the link.

**Why it matters:** Guarantees referential integrity ("no board without a real
owner"), and with `ondelete="CASCADE"` it auto-cleans dependent rows.

---

### Unique constraint

**Plain English:** A DB rule that a column (or combination) can't repeat.

**In our code:** `UniqueConstraint("board_id", "user_id")` on `memberships` means
a user can't be added to the same board twice — enforced by Postgres, not just
app code (so even a buggy double-insert is rejected).

---

### Association (join) table — many-to-many

**Plain English:** SQL can't store many-to-many directly, so you add a middle
table where each row is one pairing. Our `memberships` table pairs users ↔
boards (plus a `role`).

**Why it matters:** It's the standard pattern any time "many X relate to many Y."
Putting extra data on the relationship (here, `role`) is exactly why it's a real
table and not hidden plumbing.

---

### Forward references & TYPE_CHECKING

**Plain English:** Models reference each other (User ↔ Board), which would cause
circular imports. We avoid that by (a) importing the other model only under
`if TYPE_CHECKING:` (type-checker-only, not at runtime) and (b) writing the type
as a **string** — `Mapped[list["Board"]]`. SQLAlchemy resolves the string later.

**Why it matters:** Lets independent model files cross-reference cleanly. This
exact pattern recurs across the codebase.

---

### Fractional indexing (ordering)

**Plain English:** Give each item a `float position`; to move an item between two
others, set its position to the **average** of the neighbors. Reordering = one
`UPDATE`, no renumbering siblings.

**Tradeoff:** floats run out of precision after many inserts into the same gap →
occasional **rebalance** (renumber that one list to 1.0, 2.0, 3.0…).

**Interview angle:** know the spectrum — naive integers (renumber everything,
O(n)) → gapped integers → fractional float → LexoRank strings (Trello/Jira).
Full write-up in [`01-data-model.md`](01-data-model.md#card--list-ordering-fractional-float-positions).

---

### Hashing & salt (bcrypt)

**Plain English:** **Hashing** is one-way (can't be reversed), unlike encryption.
We store a password's bcrypt hash, never the password. A **salt** is random data
mixed in so identical passwords produce different hashes (defeats rainbow
tables); bcrypt stores the salt inside the hash string.

**In our code:** `bcrypt.hashpw(pw, bcrypt.gensalt())`. A stored hash looks like
`$2b$12$...` (`12` = cost/work factor). Verifying re-hashes the input and
compares — no decryption.

---

### JWT (JSON Web Token)

**Plain English:** A signed token `header.payload.signature`. The server signs
the payload with `SECRET_KEY`; anyone can read it, only the server can forge it.
So the server trusts a returning token **without storing a session** (stateless).

**In our code:** payload `{"sub": user_id, "exp": ...}`, signed with HS256.
`exp` makes it expire; tampering breaks the signature → rejected on decode.

**Interview angle:** "Where's the session stored?" → Nowhere server-side; the
signed token *is* the proof. Tradeoff: can't easily revoke before expiry (needs a
blocklist or refresh tokens).

---

### OAuth2 password flow & Bearer token

**Plain English:** A standard login shape: client POSTs `username`+`password` as
**form** fields, server returns a token; the client then sends
`Authorization: Bearer <token>` on later requests.

**In our code:** `OAuth2PasswordRequestForm` (login) + `OAuth2PasswordBearer`
(reading the header). Bonus: it makes the `/docs` **Authorize** button work.
Needs `python-multipart` to parse the form.

---

### Pydantic schema validation

**Plain English:** Pydantic models validate request/response data *before* your
code runs. Declare the shape; invalid input gets an automatic `422`.

**In our code:** `UserCreate` uses `EmailStr` (rejects bad emails) and
`Field(min_length=8)` (rejects short passwords). `UserRead` sets
`from_attributes=True` so FastAPI can build it straight from a SQLAlchemy object —
and it omits the password hash, so secrets never serialize out.

---

### APIRouter

**Plain English:** A mini-app you attach to the main FastAPI app to group related
routes. `APIRouter(prefix="/auth", tags=["auth"])` puts all auth endpoints under
`/auth` and groups them in `/docs`.

**Why it matters:** Keeps `main.py` tiny and the code organized by feature. We'll
add one router per resource (boards, lists, cards…).

---

## 8. Boards, Lists & Cards (Batch 2)

### Authorization via the parent resource

**Plain English:** Child resources (lists, cards) don't store their own
permissions — access is inherited from the **board** they belong to. One set of
helpers (`app/api/access.py`) resolves the parent and checks membership.

**Why it matters:** Keeps the permission model simple and the checks in one
place, instead of duplicating auth logic on every table/route.

---

### 404 vs 403 (don't leak existence)

**Plain English:** When a user asks for a board they're **not a member of**, we
return **404 Not Found**, not 403 Forbidden — so the API never confirms that the
board exists. We reserve **403** for "you're a member but not the owner" (edit/
delete), where existence is already known to them.

**Interview angle:** "Why 404 instead of 403 for another user's board?" →
information disclosure: 403 would reveal the resource exists.

---

### flush() vs commit() (atomic writes)

**Plain English:** `db.flush()` sends pending SQL to the database (so
auto-generated ids become available) but stays **inside** the transaction;
`db.commit()` makes everything permanent. Multiple inserts before one `commit()`
succeed or fail **together**.

**In our code:** `create_board` flushes to get `board.id`, adds the owner
`Membership`, then commits — so a board can never exist without its owner row.

---

### SQL JOIN in SQLAlchemy

**Plain English:** A JOIN combines rows from two tables on a matching column. We
use it to find boards a user can access by joining `boards` to `memberships`.

**In our code:**
```python
select(Board).join(Membership, Membership.board_id == Board.id)
             .where(Membership.user_id == user_id)
```
This returns boards that have a membership row for the user — the "boards I can
access" query.

---

### Nested response models

**Plain English:** Pydantic schemas can embed other schemas, so one response can
carry a whole tree. `BoardDetail` contains `ListWithCards`, which contains
`CardRead`.

**Why it matters:** `GET /boards/{id}` returns the entire board (lists + cards,
each ordered by position) in a single payload — exactly what the UI needs to
render — while still stripping any undeclared fields at every level.

---

## 9. Real-time / WebSockets (Batch 3)

### WebSocket

**Plain English:** A persistent two-way connection between browser and server.
Unlike HTTP (ask → answer → done), it stays open so the **server can push**
messages anytime — the basis of live updates.

---

### Connection rooms

**Plain English:** Grouping open connections by what they care about. We keep a
`board_id -> set of sockets` map (`ConnectionManager`), so a change to board 5 is
broadcast only to sockets watching board 5, not everyone.

---

### Sync → async bridge

**Plain English:** Our REST routes run synchronously (threadpool); WebSockets run
on the asyncio event loop. To push from sync code we schedule the async send onto
the loop with `asyncio.run_coroutine_threadsafe(coro, loop)` (the loop is captured
at startup). This is the canonical "send to a socket from sync code" answer.

---

### Query-param WebSocket auth

**Plain English:** Browsers can't set an `Authorization` header on a WS handshake,
so the client passes the JWT as `?token=...`. We validate it (and board access)
**before** accepting the socket; invalid → close with code 1008.

**Interview angle:** name the tradeoff — query tokens can land in logs; mitigations
are first-message auth or short-lived socket "tickets."

---

### Delta events vs snapshots

**Plain English:** Three ways to tell clients what changed: send a small **delta**
(`{type:"card.moved", ...}`), send a "something changed, refetch" **signal**, or
send the **whole board** every time. We use granular deltas — efficient, and the
client updates just the affected card.

---

### Lifespan (startup/shutdown)

**Plain English:** FastAPI's `lifespan` async context manager runs setup code
before the app serves requests and teardown after. We use it to capture the
running event loop for the sync→async bridge.

```python
@asynccontextmanager
async def lifespan(app):
    manager.set_loop(asyncio.get_running_loop())  # startup
    yield                                          # app runs
    # shutdown cleanup would go here
```

---

## 10. Membership & Invites (Batch 4)

### Owner-only authorization

**Plain English:** Some actions (invite/remove members, edit/delete board) are
restricted to the board **owner**, not just any member. We enforce it with one
helper, `require_board_owner`, which returns 404 if you can't see the board and
403 if you can but aren't the owner.

**Why it matters:** Centralizing the check keeps every owner-only route honest
and consistent — no scattered `if user != owner` logic.

---

### Invite an existing user by email

**Plain English:** To add a collaborator we look up an **existing** account by
email and insert a `memberships` row. No emails/links/tokens — the simplest
multi-user path.

**The payoff:** because all access flows through the `boards⋈memberships` query,
that new row instantly grants the user access to the board's lists, cards, and
WebSocket feed — no per-resource permission wiring.

---

## 11. LLM Summarizer (Batch 6)

### LLM API call (single request)

**Plain English:** The simplest way to use an LLM — one request, one response.
We send a **system** prompt (the model's role + instructions) and a **user**
message (the data), and read the text back. No tools, no loop.

**In our code:** `anthropic.Anthropic().messages.create(model, system, messages)`
with the board flattened to text as the user message. Default model is the most
capable Claude (`claude-opus-4-8`); configurable via `SUMMARIZER_MODEL`.

---

### Optional, isolated feature (config flag)

**Plain English:** A capability gated by an env var, kept in its own module so it
can be turned on/off without touching core code. All LLM code lives in
`app/services/llm.py`; the rest of the app never imports the Anthropic SDK.

**Why it matters:** Optional integrations (especially paid ones) shouldn't be
load-bearing. If the key is absent, the app runs exactly as before.

---

### Graceful degradation

**Plain English:** When an optional dependency is missing or fails, return a clear
error instead of crashing. No `ANTHROPIC_API_KEY` → `503` with
"Set ANTHROPIC_API_KEY to enable it." LLM call fails → `502`. The frontend shows
that message in the summary modal.

---

## 12. Rich Cards / Jira-style fields (G1)

Full walkthrough: `docs/08-rich-cards.md`. The concepts G1 introduced:

### Many-to-many (M2M) via an association table

**Plain English:** When *both* sides can have *many* of the other (a card has many
labels; a label is on many cards), SQL needs a third table holding just the two
foreign keys. That junction table is the "association table".

**In our code:** `card_labels(card_id, label_id)` in `app/models/associations.py`,
wired with `relationship("X", secondary=card_labels, back_populates=…)`.

**Why it matters:** It's the canonical way to model tags, roles, memberships —
anything that's a "both-ways many". The composite primary key `(card_id, label_id)`
also prevents attaching the same label twice.

---

### `server_default` vs Python `default` (backfilling a NOT NULL column)

**Plain English:** A Python `default=` only applies when *the ORM* inserts a row. A
`server_default=` writes `DEFAULT …` into the table definition, so the **database**
fills the value — including for rows that already existed before the column did.

**In our code:** `priority = mapped_column(String(20), nullable=False,
server_default="medium")`. Adding a `NOT NULL` column to a populated table only
works because Postgres backfills every existing card with `'medium'`.

**Interview angle:** *"How do you add a required column to a table that already has
data?"* → nullable + backfill + set not-null, **or** a DB-level default. We used the
default.

---

### Partial update with `exclude_unset` — the `null` vs *absent* distinction

**Plain English:** For a PATCH, you want to change only the fields the client sent.
`model_dump(exclude_unset=True)` returns only keys that were actually present in the
JSON. A key *absent* = "leave unchanged"; a key present as `null` = "clear it".

**In our code:** `payload.model_dump(exclude_unset=True)` in `PATCH /cards/{id}`.
The frontend sends `{assignee_id: null}` to unassign, and **omits** the key to keep
the assignee. (`JSON.stringify` drops `undefined` keys but keeps `null` — so the UI
passes `null`, never `undefined`/`""`, to clear a field.)

---

### Tailwind v4: only literal class names survive the build

**Plain English:** Tailwind scans your source for complete class-name *strings* and
emits CSS only for those. A class built at runtime like `` `bg-${color}-100` `` is
never seen, so its CSS is never generated → the element renders unstyled.

**In our code:** `LABEL_STYLES` in `components/CardBadges.tsx` is a static map of
allowed color → literal classes (`indigo: 'bg-indigo-100 text-indigo-700'`). The
label color picker is driven from that map's keys, so every label has a real style.

---

### Drag vs click on the same element (latching a gesture)

**Plain English:** An element that's both draggable and clickable needs to tell a
real click apart from the click the browser fires at the *end* of a drag. We latch
the library's own "is dragging" state into a `ref`; the click handler reads the
latch and ignores the click if a drag just happened.

**In our code:** `SortableCard.tsx` — `useEffect(() => { if (isDragging)
dragged.current = true })`, reset on `onPointerDownCapture`, checked in `onClick`.
Capture phase is used so our pointer handler doesn't collide with dnd-kit's
bubble-phase one. Works because a `click` targets the nearest common ancestor of
the down/up elements (see `docs/08` §5, Trap 4).

---

### Remount on reparent (why React keys are per-parent)

**Plain English:** A React `key` is unique only *among siblings under one parent*.
Move a keyed element to a **different parent** and React unmounts it and mounts a
fresh instance — local state and refs reset. Move it within the same parent and it's
preserved.

**Why it matters here:** dragging a card to another column reparents it → the card's
component remounts. We reasoned through this to prove the per-card drag latch is
still correct (the remount case is exactly the case where no click reaches the
card). It's also why the modal's draft state is keyed on `card.id`.

---

*Last updated: after G1 (rich cards — assignee/priority/due date/labels, detail
modal + badges). New concepts are appended here as we build.*
