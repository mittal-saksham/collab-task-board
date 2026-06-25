# 💻 Frontend (React + TypeScript)

The web client that consumes the API and the live WebSocket feed. This doc covers
the overall setup and the **auth foundation** (sub-batch 5a); board UI and
drag-and-drop are added in the following sub-batches.

> Status: 🟡 in progress. ✅ scaffold + auth + routing + board list/view (CRUD) ·
> ⏳ drag-and-drop, live updates, members UI.

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

➡️ Next: **@dnd-kit** drag-and-drop wired to `PATCH /cards/{id}/move`, then the
**WebSocket** feed applying live deltas to the Query cache, then the members UI.
