# Collab Task Board

A collaborative, Trello/Linear-style task board — built as a learning + portfolio
project to demonstrate real engineering: clean data modeling, JWT auth, real-time
updates, and a layered API.

**Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · PostgreSQL (Docker)
· JWT · WebSockets · React + TypeScript (frontend, planned).

---

## Status

| Feature | Status |
|---------|--------|
| Backend skeleton + Postgres + health check | ✅ |
| Data model (users, boards, memberships, lists, cards) + migration | ✅ |
| Auth — signup, login, JWT, protected routes | ✅ |
| Boards / Lists / Cards CRUD | ✅ |
| Drag-and-drop positioning (fractional, persisted) | ✅ |
| Real-time sync (WebSockets) | ✅ |
| Membership / invites | ✅ |
| React + TypeScript frontend | 🟡 auth + routing done |

---

## Quickstart

**Prerequisites:** Docker Desktop, Python 3.10+.

```bash
# 1. Start PostgreSQL (from the repo root). Reads .env automatically.
cp .env.example .env        # first time only (the committed .env already has dev values)
docker compose up -d

# 2. Create the virtualenv and install backend deps
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

# 3. Apply database migrations
cd backend
alembic upgrade head

# 4. Run the API (hot-reload)
uvicorn app.main:app --reload
```

Now open **http://127.0.0.1:8000/docs** — try `/auth/signup`, then click
**Authorize** to log in and call `/auth/me`.

> ℹ️ This project's Postgres is published on host port **5434** (not the default
> 5432) to avoid a clash with another local Postgres. See
> [`docs/CONCEPTS.md`](docs/CONCEPTS.md#localhost-binding-precedence-the-bug-we-hit).

### Frontend (in a second terminal)

```bash
cd frontend
npm install      # first time only
npm run dev      # http://localhost:5173
```

Sign up, and you're in. (The frontend expects the API at `http://localhost:8000`;
override with `VITE_API_URL` if needed.)

---

## API (so far)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/signup` | – | Create an account |
| `POST` | `/auth/login` | – | Get a JWT (form: `username`=email, `password`) |
| `GET`  | `/auth/me` | Bearer | The logged-in user |
| `POST` | `/boards` | Bearer | Create a board |
| `GET`  | `/boards` | Bearer | List boards you can access |
| `GET`  | `/boards/{id}` | Bearer | Board with all lists + cards |
| `POST` | `/boards/{id}/lists` | Bearer | Add a column |
| `POST` | `/lists/{id}/cards` | Bearer | Add a card |
| `PATCH`| `/cards/{id}/move` | Bearer | Move/reorder a card (drag-and-drop) |
| `GET`  | `/health` | – | Liveness + DB connectivity |

> Full endpoint list with request/response detail: [`docs/LLD.md`](docs/LLD.md#4-api-reference).

---

## 📚 Documentation

Written to be read cold and understood — start here:

| Doc | What's inside |
|-----|---------------|
| [`docs/HLD.md`](docs/HLD.md) | **High-level design** — architecture, components, tech rationale, flows |
| [`docs/LLD.md`](docs/LLD.md) | **Low-level design** — modules, schema, API contracts, sequence diagrams, algorithms |
| [`docs/01`–`06`](docs/) | Feature walkthroughs: data model, auth, boards/lists/cards, real-time, membership, frontend |
| [`docs/CONCEPTS.md`](docs/CONCEPTS.md) | Plain-English glossary of every concept used (grows each batch) |

---

## Repo structure

```
.
├── docker-compose.yml      # Postgres for local dev
├── .env / .env.example     # config (.env is gitignored)
├── docs/                   # HLD, LLD, concept + feature docs
└── backend/
    ├── app/
    │   ├── main.py         # FastAPI app + health
    │   ├── core/           # config + security (JWT/bcrypt)
    │   ├── db/             # engine, session, Base
    │   ├── models/         # SQLAlchemy ORM models
    │   ├── schemas/        # Pydantic request/response models
    │   ├── crud/           # data-access layer
    │   └── api/            # routers + dependencies
    ├── alembic/            # migrations
    └── requirements.txt
```
