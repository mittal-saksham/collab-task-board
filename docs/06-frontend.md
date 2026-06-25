# 💻 Frontend (React + TypeScript)

The web client that consumes the API and the live WebSocket feed. This doc covers
the overall setup and the **auth foundation** (sub-batch 5a); board UI and
drag-and-drop are added in the following sub-batches.

> Status: ✅ frontend MVP complete — auth, boards, board view, drag-and-drop,
> live updates, members.

---

## Stack & why

| Concern | Choice | Why |
|---------|--------|-----|
| Build/dev | **Vite** | Fast dev server + instant HMR |
| Language | **TypeScript** | Type-safe UI; types mirror the API (`src/types.ts`) |
| Server state | **TanStack Query** | Caching, refetch, optimistic updates; WS events apply to its cache |
| Routing | **React Router** | Login/signup vs. protected app routes |
| Styling | **Tailwind CSS v4** | Fast, custom board UI via utility classes |
| Drag & drop | **@dnd-kit** (next) | Modern, accessible card/column dragging |

---

## Structure

```
frontend/src/
├── main.tsx              # providers: QueryClient + Router + Auth
├── App.tsx               # route table
├── index.css             # @import "tailwindcss";
├── types.ts              # User, Board, List, Card, BoardDetail (mirror the API)
├── lib/
│   └── api.ts            # fetch wrapper: base URL, JWT header, JSON, ApiError
├── auth/
│   ├── AuthContext.tsx   # user + login/signup/logout (token in localStorage)
│   └── ProtectedRoute.tsx# redirects to /login when not authed
└── pages/
    ├── LoginPage.tsx
    ├── SignupPage.tsx
    └── BoardsPage.tsx     # (placeholder; real board list next)
```

---

## The auth flow (frontend side)

This mirrors [`02-auth.md`](02-auth.md) from the client's perspective.

1. **API client (`lib/api.ts`)** — every request goes through `apiFetch`, which
   reads the JWT from `localStorage` and sets `Authorization: Bearer <token>`.
   Non-2xx responses throw an `ApiError` carrying the backend's `detail` message.
   `login()` posts **form-encoded** `username`/`password` (the OAuth2 flow).

2. **AuthContext (`auth/AuthContext.tsx`)** — holds the current `user` and exposes
   `login`, `signup`, `logout`. On mount, if a token exists it calls `/auth/me`
   to restore the session (and clears a bad/expired token). `signup` auto-logs-in
   afterward.

   > 🧠 **React Context:** a way to share state (here, "who's logged in") with any
   > component without passing props down every level. Components read it via our
   > `useAuth()` hook.

3. **ProtectedRoute (`auth/ProtectedRoute.tsx`)** — a guard route: shows a loader
   while the session is being checked, redirects to `/login` if there's no user,
   else renders the matched child via `<Outlet />`.

4. **Providers (`main.tsx`)** — `QueryClientProvider` → `BrowserRouter` →
   `AuthProvider` wrap `<App />` so every component can use Query, routing, and
   auth.

**Verified in a browser:** signup → auto-login → redirect to `/boards`; token in
`localStorage`; the session **survives a page reload**; CORS works between the
Vite dev server (`:5173`) and the API (`:8000`).

> 🔐 **localStorage tradeoff (recap):** simple and works with our Bearer-header
> requests and the WS query-param token, but readable by JS (XSS risk). Documented
> choice for the MVP.

---

## Talking to the backend

- Base URL is `import.meta.env.VITE_API_URL` (defaults to `http://localhost:8000`).
- The backend enables **CORS** for `http://localhost:5173` (the Vite origin) — see
  `backend/app/main.py`. Browsers block cross-origin calls unless the server sends
  these headers.

---

## Run it

```bash
# backend must be running (see root README), then:
cd frontend
npm install      # first time
npm run dev      # http://localhost:5173
```

## Board UI & TanStack Query (5b)

- **`hooks.ts`** wraps the API in Query hooks. `useBoards()`/`useBoard(id)` cache
  data by a **queryKey** (`['board', 5]`). Mutations (`useBoardMutations`) call the
  REST endpoints and then `invalidateQueries` so the affected query **refetches**
  and the UI updates — no manual state juggling.

  > 🧠 **TanStack Query in one line:** `useQuery` reads+caches; `useMutation`
  > writes; invalidating a queryKey triggers a refetch. The cache is the single
  > source of truth the UI renders from.

- **Pages/components:** `BoardsPage` (list + create boards) → links to
  `BoardPage` (`/boards/:boardId`), which renders `Column`s of `CardItem`s with
  inline "add list / add card" forms. `AppHeader` shows the user + logout.

Verified in a browser: create board → open → add list → add card all render via
Query refetch.

## Drag-and-drop (5c)

- **@dnd-kit**: each card is a `useSortable` (`SortableCard`), each column a
  `useDroppable` wrapping a `SortableContext`. A `PointerSensor` with a 5px
  activation distance keeps plain clicks (the × button) working.
- On **`onDragEnd`** we figure out the target list and the card dropped onto,
  compute **`after_id`** (the card to sit behind, or `null` for the front), update
  local state **optimistically**, then call `PATCH /cards/{id}/move`. The board
  query refetches on success and re-syncs.

  > 🧠 The frontend computes *where* (target list + `after_id`); the backend
  > computes the actual float **position** (midpoint). Clean split of concerns.

Verified in a browser: dragging a card `To Do → Doing` moved it and **persisted**
(confirmed via the API).

## Live updates (5d)

- **`useBoardLiveUpdates(boardId)`** opens `WS /ws/boards/{id}?token=…` (token as a
  query param, since the browser can't set an Auth header on a WS handshake). On
  **any** event it invalidates `['board', id]` so the board refetches. The socket
  closes on unmount.
- Net effect: when *anyone* changes the board, every open viewer updates within a
  moment — no refresh.

Verified in a browser: a card created by a **separate** API client appeared in the
open board live, with no manual refresh.

## Members UI (5e)

- **`MembersPanel`** (a dropdown in the board header) lists members via
  `useMembers`. The **owner** sees an invite-by-email form and remove buttons;
  others just see the list (`isOwner = user.id === board.owner_id`).
- Member changes also arrive live — `useBoardLiveUpdates` invalidates the
  `['members', id]` query on WS events too.

Verified in a browser: owner invited a teammate by email → appeared in the list
(`owner` + `member`), persisted via the API.

➡️ The frontend MVP is done. Next (optional stretch): the **LLM board summarizer**.
