# 08 · Rich Cards (Jira-style) — assignee, priority, due date, labels

**Status:** ✅ Done (backend + frontend), verified non-breaking.

This is the first of four "make it more Jira-like" feature groups (G1–G4). It
turns a card from `{title, description}` into a small issue: it can be **assigned**
to a member, carry a **priority**, have a **due date**, and wear colored **labels**.
On the board each card now shows compact **badges**; clicking a card opens a
**detail modal** to edit everything.

The hard rule for this whole effort: **strictly additive**. Existing rows, API
calls, and UI all keep working unchanged. Every new column is nullable or has a
DB-level default; every new field on the API response has a default; the board
endpoint's shape only grew.

---

## 1. Data model changes

Two new things on top of the original 5 tables (see `docs/01-data-model.md`).

### 1a. New columns on `cards`

| Column | Type | Notes |
|---|---|---|
| `assignee_id` | `int?` FK → `users.id` | `ON DELETE SET NULL` — deleting a user nulls the assignment, never deletes the card |
| `priority` | `str` | `NOT NULL`, **DB-level** `server_default='medium'` |
| `due_date` | `date?` | nullable |

**Why `server_default` and not a Python default?** A Python-side `default="medium"`
only fires when *the ORM* inserts a row. The migration has to backfill the column
on rows that **already exist** in the DB — and those are filled by Postgres, not by
Python. `server_default='medium'` emits `DEFAULT 'medium'` in the DDL, so Postgres
itself fills every existing card. Without it, adding a `NOT NULL` column to a table
with rows fails outright.

> Reviewer question to expect: *"How did existing cards get a priority?"* →
> "The column is `NOT NULL DEFAULT 'medium'` at the database level, so Postgres
> backfilled all pre-existing rows during the migration."

### 1b. Labels — a many-to-many

A **label** is a colored tag scoped to one board. A card can have many labels; a
label can be on many cards → a classic **many-to-many (M2M)**, which in SQL needs a
third **association table**:

```
labels(id, board_id→boards, name, color)
card_labels(card_id→cards, label_id→labels)     ← association/junction table
```

`card_labels` has just the two foreign keys as a composite primary key. Both FKs
are `ON DELETE CASCADE`, so deleting a card or a label automatically removes its
join rows (no orphans).

---

## 2. The SQLAlchemy M2M gotcha (the one that cost real time)

This is the most important *why* in G1 — worth being able to explain.

We model the relationship with `secondary=` (point SQLAlchemy at the association
table) and `back_populates` (keep both sides in sync):

```python
# app/models/associations.py — the association table, defined ONCE, imported by both sides
card_labels = Table(
    "card_labels", Base.metadata,
    Column("card_id",  ForeignKey("cards.id",  ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)
```

```python
# Card  ── note: NO `Mapped[list["Label"]]` annotation
labels = relationship("Label", secondary=card_labels, back_populates="cards")
# Label
cards  = relationship("Card",  secondary=card_labels, back_populates="labels")
```

**The trap:** the modern SQLAlchemy 2.0 style is to *annotate* relationships like
`labels: Mapped[list["Label"]] = relationship(...)`. For a M2M whose target is a
**string forward-reference in another module** plus a `secondary=` table,
SQLAlchemy could not reliably read that annotation to figure out the collection
type. The symptom was nasty and *silent at import time* — mappers configure
**lazily** (on first query), so `import app.models` succeeded and only the first
real request blew up. We saw, in sequence:

1. `relationship 'labels' expects a class … (received: NotImplementedType)` — login 500'd.
2. After adding the explicit `"Label"` string: it resolved, but came back as a
   **scalar** (`uselist=False`), so `card.labels` was `None`, not a list → the
   response schema (`labels: list[LabelRead]`) failed validation.

**The fix:** drop the `Mapped[list[...]]` annotation on **both** M2M sides and use
a plain, non-annotated `relationship("X", secondary=…, back_populates=…)`. Without
the annotation, a `secondary` relationship correctly defaults to a list. At runtime
`card.labels` is a normal Python list.

> Rule of thumb learned: **single-file** M2M is fine fully annotated; **cross-module**
> M2M with `secondary=` → use the non-annotated form. Scalar FKs (like
> `assignee: Mapped[Optional["User"]] = relationship("User")`) keep the annotation;
> only the `secondary` collections drop it.

---

## 3. API surface (all additive)

### Editing a card — `PATCH /cards/{id}` and the `exclude_unset` pattern

`CardUpdate` makes **every** field optional. The route then applies only the keys
the client actually sent:

```python
fields = payload.model_dump(exclude_unset=True)   # only keys present in the JSON
card = card_crud.update_card(db, card, fields)     # whitelist-applied in CRUD
```

This is the crux of partial updates and it hinges on a `null` vs *absent*
distinction:

- **Key absent** → field left unchanged.
- **Key present with `null`** (e.g. `{"assignee_id": null}`) → field is **cleared**.

So "unassign" and "clear due date" must send an explicit `null`, while leaving a
field alone means *omit the key*. (The frontend mirrors this carefully — see §5.)

Assigning someone also validates they're a **board member** (else `400`):

```python
if fields.get("assignee_id") is not None:
    if membership_crud.get_membership(db, board_id, fields["assignee_id"]) is None:
        raise HTTPException(400, "Assignee must be a member of this board")
```

### Labels router (`app/api/labels.py`)

| Method & path | Does |
|---|---|
| `GET /boards/{id}/labels` | list a board's palette |
| `POST /boards/{id}/labels` | create a label (`name`, `color`) |
| `DELETE /labels/{id}` | delete a label (join rows cascade) |
| `PUT /cards/{cid}/labels/{lid}` | attach a label to a card → returns the updated card |
| `DELETE /cards/{cid}/labels/{lid}` | detach → returns the updated card |

Every mutation `emit()`s a WebSocket event (`label.created`, `label.deleted`,
`card.updated`) so other clients refresh live — consistent with the rest of the app.

### The board payload only grew

`GET /boards/{id}` returns `BoardDetail → lists → ListWithCards → CardRead`, and
`CardRead` gained `priority`, `due_date`, `assignee` (a `UserBrief | null`), and
`labels` (`LabelRead[]`). Because these are **additions with defaults**, old
clients ignore them and the new UI renders everything from this **one existing
query** — no extra round-trip to draw badges.

---

## 4. Frontend — badges + the detail modal

### Components added / changed

| File | Role |
|---|---|
| `components/CardBadges.tsx` | shared badge row (priority dot, due chip, assignee avatar, label chips) — used by both the on-board card and the drag overlay |
| `components/CardModal.tsx` | the detail/edit modal (self-contained) |
| `components/SortableCard.tsx` | added click-to-open + the drag-vs-click guard |
| `components/Column.tsx`, `pages/BoardPage.tsx` | thread `onOpenCard` and render the modal |
| `lib/boards.ts`, `hooks.ts`, `types.ts` | new API calls, query/mutations, types |

The modal is **self-contained**: given a `card` and `boardId`, it pulls the board's
members (assignee dropdown) and label palette itself via `useMembers` / `useLabels`,
and writes through `useBoardMutations`. The parent renders it **keyed on
`card.id`**, which matters (see §5).

---

## 5. Four frontend traps worth knowing (these were the real work)

These are the bugs that *don't* throw — the UI just silently does the wrong thing.
Anticipate all four in review.

### Trap 1 — Tailwind v4 drops dynamically-built color classes

Tailwind only emits CSS for classes it can see as **complete string literals** at
build time. `` `bg-${color}-100` `` compiles to nothing → colorless chips. Fix: a
**static map** of allowed colors → literal classes, and the new-label color picker
is driven from that map's keys so you can't create a color with no style:

```ts
export const LABEL_STYLES: Record<string, string> = {
  slate: 'bg-slate-100 text-slate-700',
  indigo: 'bg-indigo-100 text-indigo-700',  // …one literal line per allowed color
}
```

### Trap 2 — `undefined` won't clear a field; you need `null`

`JSON.stringify({assignee_id: undefined})` → `{}` (key dropped) → backend's
`exclude_unset` reads "no change". So "Unassigned" / "clear due date" emit an
explicit `null`:

```tsx
patch({ assignee_id: e.target.value ? Number(e.target.value) : null })
patch({ due_date: e.target.value || null })
```

### Trap 3 — a background refetch can clobber what you're typing

The open card is derived live from the board query, but title/description are also
held in local draft state. If you re-sync that draft on every `card` change, a WS
event or refetch overwrites the user's keystrokes. Fix: initialize the draft
**once**. We do it by keying the modal on `card.id` (`<CardModal key={card.id} …>`),
so it remounts only when a *different* card opens; `useState(card.title)` then
initializes exactly once. Selects/date fire on change immediately, so they read
straight from `card` (no draft) and don't have this problem.

### Trap 4 — dragging a card must not open the modal

A card is both **draggable** (dnd-kit) and **clickable** (open modal). After a real
drag-and-drop the browser can fire a `click`, which would wrongly open the modal.

**The guard (in `SortableCard`):** latch dnd-kit's own drag state.

```tsx
const dragged = useRef(false)
useEffect(() => { if (isDragging) dragged.current = true }, [isDragging])
// on the card:
onPointerDownCapture={() => { dragged.current = false }}   // capture phase: doesn't
                                                           // collide with dnd-kit's
                                                           // bubble-phase onPointerDown
onClick={() => { if (dragged.current) { dragged.current = false; return } onOpen() }}
```

A plain click never enters drag state → `dragged` stays false → opens. Any real
drag flips `isDragging` true at some point → `dragged` latched → the trailing click
is swallowed.

**Why a per-card ref is enough (the subtle part).** A `click` event targets the
**nearest common ancestor of the pointerdown and pointerup elements**:

- *Cross-column drag* (down on a card in one column, up on a card in another): the
  common ancestor is the board container, so the `click` never reaches *either*
  card's `onClick`. (It's irrelevant that the card unmounts/remounts when it
  changes column — its handler isn't the click target.)
- *Drop-in-place / drop-on-self* (down and up on the **same** card): that card is
  the click target — but it never changed column, so it never remounts, so the
  `dragged` ref survives and suppresses the click.

The one case that fires a card's own click is also the one case where the ref is
guaranteed intact. No timestamp/magic-number needed.

Also: the `×` delete button does `e.stopPropagation()` on click so deleting never
bubbles up to open the modal.

---

## 6. How it was verified non-breaking

- **Migration round-trip:** `upgrade` then `downgrade` then `upgrade` cleanly; the
  downgrade explicitly drops the named FK `cards_assignee_id_fkey`. A DB backup was
  taken first (`scratchpad/backups/pre-g1.sql`).
- **Backfill:** all pre-existing cards came out `priority='medium'`, `assignee=None`,
  `labels=[]`.
- **Regressions still pass:** drag-move, members, summarize all behave as before.
- **New behavior (API):** set priority/due/assignee, attach/detach label,
  assign-non-member → `400`, unassign with `null` → assignee `None`.
- **New behavior (UI, Playwright):** plain click opens the right card; editing
  persists to the DB; unassign sends literal `null`; badges reflect saved edits; a
  cross-column drag moves the card and an in-place drag does **not** open the modal,
  while a fresh click does; `×` deletes without opening; creating + attaching a
  label shows a chip on the board with a real (non-dropped) Tailwind color.

---

*Part of the Jira-style feature set: G1 rich cards (this doc) → G2 comments +
activity log → G3 issue types + story points + WIP limits → G4 search/filter bar.*
