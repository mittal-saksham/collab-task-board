# 11 · Search / Filter Bar (Jira-style G4)

**Status:** ✅ Done (frontend only), verified non-breaking.

The fourth and final Jira-style group: a bar above the board that filters which
cards are shown — by **free text**, **assignee**, **label**, **priority**, and
**issue type**. Filters combine with AND (a card must match all active ones).

This group is **frontend-only**. There is no new endpoint and no DB change: the
whole board (all lists + cards) is already loaded by the existing `useBoard`
query, so filtering is pure client-side work on data we already have.

> Why client-side? At board scale (tens–hundreds of cards) it's instant, needs
> zero backend work, and keeps the live-update story simple. Server-side search
> only earns its complexity at much larger scale.

---

## 1. The filter model (`lib/filters.ts`)

```ts
interface Filters {
  text: string       // substring of title + description
  assignee: string   // 'any' | 'unassigned' | "<userId>"
  label: string      // 'any' | "<labelId>"
  priority: string   // 'any' | a priority value
  issueType: string  // 'any' | 'task' | 'bug' | 'story'
}
```

Every field is a **string** (ids stored as strings, special sentinels `'any'` /
`'unassigned'`) so each maps cleanly onto a `<select>` value. Three pure helpers:

- `EMPTY_FILTERS` — the reset state.
- `filtersActive(f)` — is anything narrowing the view? (drives the "Clear" button
  and the "showing X of Y" count, and whether we filter at all).
- `cardMatches(card, f)` — the predicate, one `return false` per failed filter:

```ts
if (f.assignee === 'unassigned') { if (card.assignee) return false }
else if (f.assignee !== 'any')   { if (card.assignee?.id !== Number(f.assignee)) return false }
if (f.label !== 'any' && !card.labels.some(l => l.id === Number(f.label))) return false
// …priority, issueType, text…
```

Keeping these as **pure functions in a lib file** (not buried in a component)
makes them trivial to reason about and reuse.

---

## 2. Wiring (who owns what)

- **`BoardPage`** owns the `filters` state. It computes `matchCount` and, per
  column, the `visibleCards` to render:
  ```tsx
  visibleCards={active ? list.cards.filter(c => cardMatches(c, filters)) : list.cards}
  ```
- **`FilterBar`** is a self-contained control strip. It owns *no* filter state —
  it just renders the inputs and calls `onChange`. It pulls the board's members
  and labels itself (`useMembers`/`useLabels`) to populate the dropdowns.

---

## 3. The two things that had to stay correct (non-breaking)

This group touches the board render path, so two existing behaviors had to be
preserved deliberately:

### a) The WIP count must stay the FULL count

`Column` now receives `visibleCards` (filtered) **separately** from `list` (full).
The cards it renders come from `visibleCards`, but the WIP badge counts
`list.cards.length`. So filtering the *view* never changes the *count* — a column
with a `2 / 1` WIP badge still reads `2 / 1` even when a search hides one of those
two cards. (If the badge used the filtered list, the WIP signal would lie.)

### b) Drag-and-drop must not break

The drag handlers in `BoardPage` (`findCard`, `onDragEnd`) operate on the full
`lists` state, **not** on the filtered view. And crucially, when no filter is
active, `visibleCards` is literally `list.cards` (same array) — so the default
board is byte-for-byte the pre-G4 render path. Dragging with a filter applied
still works (positions resolve against the full list); dragging with no filter is
exactly as before.

> Verified after G4: a cross-column drag still moves a card and persists to the
> backend, unchanged.

---

## 4. How it was verified

UI (Playwright), against a 2-card board:

- No filter → both cards shown, no "showing" count, WIP badge `2 / 1`.
- Search `"wire"` → only the matching card shown, **"Showing 1 of 2"**, WIP badge
  still `2 / 1` (full count unaffected).
- Type = `story` → only the story card shown.
- **Clear** → both cards back, count hidden.
- Drag regression → a card still moves across columns and persists.
- `npm run build` passes.

---

*Completes the Jira-style set: G1 rich cards → G2 comments + activity log → G3
issue types + story points + WIP limits → G4 search/filter bar (this doc).*
