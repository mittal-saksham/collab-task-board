# 10 · Issue Types + Story Points + WIP Limits (Jira-style G3)

**Status:** ✅ Done (backend + frontend), verified non-breaking.

The third Jira-style group adds three small-but-meaningful fields:

- **Issue type** — every card is a `task`, `bug`, or `story` (shown as a colored
  glyph badge).
- **Story points** — an optional effort estimate per card.
- **WIP limit** — a per-column soft cap on card count. **Display-only** (see §3).

All three are **strictly additive**: nullable or DB-defaulted columns, no change to
any existing behavior. This was the simplest group precisely because of the
patterns G1 already established — the only *design* question was the WIP limit.

---

## 1. Data model (three additive columns)

| Column | Type | Notes |
|---|---|---|
| `cards.issue_type` | `str` NOT NULL | **`server_default='task'`** → existing cards backfill to `task` |
| `cards.story_points` | `int?` | nullable estimate |
| `lists.wip_limit` | `int?` | nullable; `NULL` = no limit |

`issue_type` reuses the **exact `server_default` trick from G1** (`docs/08` §1a):
a DB-level default so Postgres backfills every pre-existing row when the `NOT NULL`
column is added. `story_points` and `wip_limit` are simply nullable, so no
backfill is needed at all.

> Verified: after the migration, all 8 existing cards were `issue_type='task'`,
> `story_points=NULL`, and all 10 lists `wip_limit=NULL`. Migration round-trips.

---

## 2. API (additive)

- **Cards:** `CardUpdate`/`CardRead` gained `issue_type` (a `Literal["task","bug",
  "story"]`, so an invalid value is a `422`) and `story_points` (`int`, `ge=0`,
  `le=999`). The whitelist in `crud/card.update_card` was extended, so the same
  `PATCH /cards/{id}` with `exclude_unset` handles them — including `story_points:
  null` to clear an estimate.
- **Lists:** `PATCH /lists/{id}` already existed for renaming. Its `ListUpdate`
  schema was widened from a *required* `title` to **both fields optional**
  (`title`, `wip_limit`) and the route switched to `exclude_unset`. So you can now
  set the WIP limit independently of the title.

### Why making `ListUpdate` fields optional matters

Before G3, `ListUpdate.title` was required, and the route did `update_list(...,
title=payload.title)`. If we'd just *added* `wip_limit` and kept that pattern,
setting only the limit would also have forced a title. Switching to the same
`model_dump(exclude_unset=True)` + whitelist pattern the cards use makes each field
independently settable — and a rename no longer touches `wip_limit`.

> Verified: `PATCH /lists/{id} {"title": "To Do"}` left a previously-set
> `wip_limit=3` untouched. That's the `exclude_unset` guarantee in action.

---

## 3. The one design decision: WIP limit = **display-only**

A WIP limit *could* be enforced (reject a move/create that overflows a column).
We deliberately chose **display-only**, for a specific reason tied to the project's
hard rule ("don't break the existing app"):

- **Enforcing** would change the behavior of the already-shipping drag flow: an
  over-limit drop would `400`, the optimistic move would snap back, and to the user
  that reads as *"the drag broke."* That's a behavior change to a core feature.
- **Display-only** is purely additive: we show `count / limit` on the column
  header and turn it **red when over**, but nothing blocks a drop. This is also
  what most Trello/Jira-clone portfolios actually do.

So `wip_limit` is advisory. The backend never references it in the create/move
routes — it's only stored and returned. All the "is this column over?" logic lives
in the UI.

> Reviewer question to expect: *"Does the WIP limit stop me from adding cards?"* →
> "No — it's a display-only signal. Enforcing it would change the existing
> drag-and-drop behavior, which we kept stable. Easy to make it enforce later: add
> a count check in the create/move routes."

---

## 4. Frontend

| File | Change |
|---|---|
| `components/CardBadges.tsx` | `ISSUE_TYPE` map (glyph + color per type) and a `story_points` pill; both added to the card's badge row. Exports `ISSUE_TYPES` for the modal. |
| `components/CardModal.tsx` | sidebar gained a **Type** select and a **Story points** number input (empty → `null`). |
| `components/Column.tsx` | header shows `count` (and `/ limit` if set), **red when over**; clicking it opens an inline number input to set/clear the limit. |
| `lib/boards.ts`, `hooks.ts` | `CardPatch` gained the two card fields; new `updateList(id, patch)` + `useBoardMutations().updateList`. |

### The inline WIP editor (uncontrolled input + commit)

The column's limit editor is a small **uncontrolled** number input
(`defaultValue`, not `value`): you click the badge, type a number, and it commits
on blur/Enter:

```tsx
function commitWip(value: string) {
  const n = parseInt(value, 10)
  onSetWipLimit(Number.isFinite(n) && n >= 1 ? n : null) // empty/0/NaN → clear
  setEditingWip(false)
}
```

Sending `null` clears the limit — the same null-to-clear pattern as the card
fields, flowing through `PATCH /lists/{id}` with `exclude_unset`.

---

## 5. How it was verified non-breaking

- **Migration:** three `ADD COLUMN`s; `issue_type` carries a DB default so existing
  rows backfill. Round-trips (`upgrade`→`downgrade`→`upgrade`). Backup at
  `scratchpad/backups/pre-g3.sql`.
- **API:** set `issue_type`/`story_points`; clear points with `null`; invalid
  `story_points=-1` and `issue_type='epic'` → `422`; set `wip_limit=3`;
  **rename-only PATCH preserved `wip_limit`**; clear `wip_limit` with `null`;
  invalid `wip_limit=0` → `422`. Board detail still loads with the new fields.
- **UI (Playwright):** card badges render the type glyph + points pill; the modal's
  Type and Story-points edits persist to the DB and update the badge; a column's
  WIP badge shows `2 / 1` in **red** after setting a limit below its count.
  `npm run build` passes.

---

*Part of the Jira-style set: G1 rich cards → G2 comments + activity log → G3 issue
types + story points + WIP limits (this doc) → G4 search/filter bar.*
