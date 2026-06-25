# 09 · Comments + Activity Log (Jira-style G2)

**Status:** ✅ Done (backend + frontend), verified non-breaking.

The second Jira-style group. It adds two collaboration features:

- **Comments** — a discussion thread on each card (post, read, delete-your-own).
- **Activity log** — a per-board, append-only feed of what happened ("Alice
  created card X", "Bob moved Y to Doing", "Carol commented on Z").

Like G1, everything is **strictly additive**: two brand-new tables, new routes,
and new UI. No existing column, route, or component changed behavior — the
activity rows are written as a *side-effect* of existing routes via a best-effort
helper that can never break the primary action.

---

## 1. Data model — two new tables

```
comments(id, card_id→cards CASCADE, author_id→users CASCADE, body, created_at)
activities(id, board_id→boards CASCADE, actor_id→users SET NULL,
           card_id→cards SET NULL, verb, summary, created_at)
```

### Why these `ON DELETE` choices

| FK | Rule | Reason |
|---|---|---|
| `comments.card_id` | CASCADE | delete a card → its thread goes too |
| `comments.author_id` | CASCADE | delete a user → their comments go too |
| `activities.actor_id` | **SET NULL** | the history line survives even if the user is later removed |
| `activities.card_id` | **SET NULL** + nullable | some events have no card (member added); deleting a card must keep the record that it once existed — the `summary` already captured its title |

The activity table is **append-only**: rows are never edited, only inserted and
read back as a feed. `verb` is a short machine code (`created_card`, `commented`,
…) and `summary` is the pre-rendered human line (so the frontend renders nothing).

---

## 2. The cross-cutting concern: how activities get written

Activities are produced by *many* routes (create card, move card, comment, …).
Rather than copy insert-and-broadcast logic everywhere, there's one helper:

```python
# app/services/activity_log.py
def log(db, *, board_id, actor_id, verb, summary, card_id=None) -> Activity | None:
    try:
        activity = activity_crud.record(db, board_id=..., verb=..., summary=...)
        emit(board_id, "activity.created", ActivityRead...model_dump(mode="json"))
        return activity
    except Exception:
        db.rollback()      # never let a logging hiccup break the real mutation
        return None
```

Two deliberate properties:

1. **It bundles the DB write with the `activity.created` WebSocket broadcast**, so
   every event also notifies live watchers — consistently, in one call.
2. **It is best-effort.** Activity logging is secondary. The whole body is wrapped
   in `try/except`: if it fails, we roll back *only* the activity insert (the
   primary mutation already committed earlier in the route) and return `None`. A
   bug in logging can never turn a successful "create card" into a 500.

> Reviewer question to expect: *"Isn't writing the activity in the route a layering
> smell?"* → It's a pragmatic choice. The alternative (SQLAlchemy event listeners /
> an outbox) is more decoupled but much heavier; for this size, an explicit
> `activity_log.log(...)` call in each route is readable and easy to reason about.

Routes that log today: card **create / update / move / delete** (`api/cards.py`)
and **member added** (`api/members.py`) and **comment posted** (`api/comments.py`).

---

## 3. API surface (all additive)

### Comments

| Method & path | Who | Notes |
|---|---|---|
| `GET /cards/{id}/comments` | any board member | oldest-first |
| `POST /cards/{id}/comments` | any board member | `body` (1–5000 chars); also logs a `commented` activity |
| `DELETE /comments/{id}` | the **author only** | `403` if you didn't write it, `404` if it's gone |

`CommentRead` embeds the author as a `UserBrief` (id + email), built straight from
the ORM relationship via `from_attributes`.

### Activity feed

| Method & path | Who | Notes |
|---|---|---|
| `GET /boards/{id}/activities` | any board member | newest-first, capped at 50 |

This route is **read-only** — it never writes. The rows come from `activity_log`.

---

## 4. Frontend

### New pieces

| File | Role |
|---|---|
| `components/CommentThread.tsx` | the thread inside the card modal (list + add box; delete-your-own) |
| `components/ActivityPanel.tsx` | a header dropdown (mirrors `MembersPanel`) showing the board feed |
| `lib/time.ts` | `timeAgo()` ("just now", "5m ago", "2d ago") + `initials()` |
| `hooks.ts` | `useComments(cardId)`, `useActivities(boardId)`, `createComment`/`deleteComment` mutations |

### Live updates

`useBoardLiveUpdates` already invalidates the board/members/labels queries on any
WS event. G2 adds two more: `['activities', boardId]` and `['comments']`. Comments
are keyed *per card* and the WS event doesn't say which card changed, so we
invalidate **all** comment queries by prefix — only the open card's thread is
actually mounted, so this is cheap. Net effect: another user's comment or any
activity shows up live without a refresh.

### Mutation variables carry the cache key

Comments are card-scoped, but `useBoardMutations` is board-scoped. The trick is to
pass `cardId` through the mutation's *variables* and read it in `onSuccess`:

```ts
createComment: useMutation({
  mutationFn: (v: { cardId: number; body: string }) => api.createComment(v.cardId, v.body),
  onSuccess: (_data, v) => {            // <-- v is the variables you passed to .mutate()
    qc.invalidateQueries({ queryKey: ['comments', v.cardId] })
    qc.invalidateQueries({ queryKey: ['activities', boardId] })
  },
})
```

---

## 5. UI polish pass (light theme)

Alongside G2, the card modal was restyled (still light theme, per the chosen
direction) into a **content + sidebar** layout, like Linear/Jira:

- **Left (main):** title, description, and the comment thread.
- **Right (sidebar):** the properties — assignee, priority, due date, labels.
- Softer container (`rounded-xl`, `ring-1`, `shadow-2xl`), a header divider, and
  consistent uppercase section labels.

Purely visual — every handler (the G1 null-clear PATCH semantics, label
attach/detach/delete) is unchanged, just rearranged.

---

## 6. How it was verified non-breaking

- **Migration:** two `CREATE TABLE`s only — nothing on existing tables. Round-trips
  (`upgrade`→`downgrade`→`upgrade`) cleanly. Backup at `scratchpad/backups/pre-g2.sql`.
- **Comments (API):** GET empty → POST 201 → empty body `422` → list shows it →
  author delete `204` → delete-again `404` → **non-author delete `403`**.
- **Activity (API):** posting a comment, creating/moving/deleting a card each
  appended the expected `verb` to `GET /activities`.
- **Regressions (API):** board detail, members, and summarize all unchanged.
- **UI (Playwright):** post a comment (appears, input clears), delete own comment
  (row removed, modal stays open), the Activity panel lists events with actor +
  relative time, and — since the modal was rewritten — a sidebar **priority edit
  still persists** to the DB. `npm run build` passes.

---

*Part of the Jira-style set: G1 rich cards → G2 comments + activity log (this doc)
→ G3 issue types + story points + WIP limits → G4 search/filter bar.*
