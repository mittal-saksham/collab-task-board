# ✨ LLM Board Summarizer (optional)

The one AI feature — a "Summarize" button that asks **Claude** to describe a
board in a few sentences. It's deliberately **optional and isolated**: the entire
feature turns on or off with a single env var and touches nothing in the core
app.

> Status: ✅ built. Disabled by default — set `ANTHROPIC_API_KEY` to enable.

---

## How it's isolated

Everything LLM-specific lives in **`app/services/llm.py`**. The rest of the app
never imports the Anthropic SDK. If `ANTHROPIC_API_KEY` is unset:
- `llm.summarize_board()` raises `SummarizerNotConfigured`,
- the route returns **`503`** with a clear message,
- nothing else is affected.

This is the "feature flag via config" pattern: an optional capability gated by an
env var, failing gracefully when absent.

---

## The flow

```
Click "✨ Summarize"
   → POST /boards/{id}/summarize            (member-only; 503 if no key)
   → gather the board's columns + cards as plain text
   → Claude (Anthropic SDK): messages.create(model, system, user=board text)
   → return { "summary": "..." }
   → frontend shows it in a modal
```

---

## Backend (`app/services/llm.py`)

> 🧠 **LLM API call (single request):** the simplest LLM usage — one request, one
> response. We send a **system** prompt (the assistant's role + instructions) and
> a **user** message (the board's contents), and read the text back.

```python
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
response = client.messages.create(
    model=settings.summarizer_model,     # default: claude-opus-4-8
    max_tokens=1024,
    system=SYSTEM_PROMPT,                # "concise project assistant…"
    messages=[{"role": "user", "content": board_text}],
)
summary = "".join(b.text for b in response.content if b.type == "text").strip()
```

- **`board_text`** is built by `_board_to_text()` — it flattens columns and cards
  (and descriptions) into a plain-text outline the model reads.
- **Model:** defaults to the most capable (`claude-opus-4-8`). Set
  `SUMMARIZER_MODEL=claude-haiku-4-5` for a cheaper, faster summary.
- **Errors:** SDK failures (auth, rate limit, network) become `SummarizerError`
  → the route returns **`502`**. Missing key → `SummarizerNotConfigured` → **`503`**.

**Route** (`app/api/boards.py`): `POST /boards/{id}/summarize`, member-gated,
returns `BoardSummary { summary }`. Rate-limited to 5/min per IP
(`core/ratelimit.py` — each call costs real Anthropic API money), so a busy
finger also sees **`429`** with a `Retry-After` header. Upstream errors are
logged server-side and returned as a generic 502 (no raw provider text).

---

## Frontend

- `useSummarizeBoard(id)` — a TanStack Query **mutation** (it's an action, not
  cached data) that POSTs to the endpoint.
- The **"✨ Summarize"** button in the board header triggers it and opens a modal
  showing the loading state, the returned summary, or the error message (so a
  missing-key `503` reads as "Set ANTHROPIC_API_KEY to enable it.").

---

## Enabling it

1. Get a key from <https://console.anthropic.com/>.
2. Add it to your repo-root `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   # optional: SUMMARIZER_MODEL=claude-haiku-4-5
   ```
3. Restart the backend. The button now returns a real summary.

> 💰 Each click is one Claude API call billed to your key. The default
> `claude-opus-4-8` is the most capable; `claude-haiku-4-5` is the cheapest.

---

## File map

| File | Role |
|------|------|
| `app/services/llm.py` | the isolated Claude call + `_board_to_text` |
| `app/api/boards.py` | `POST /boards/{id}/summarize` route (503/502 handling) |
| `app/schemas/board.py` | `BoardSummary` response |
| `app/core/config.py` | `anthropic_api_key`, `summarizer_model` settings |
| `frontend/src/lib/boards.ts` · `hooks.ts` | `summarizeBoard` + `useSummarizeBoard` |
| `frontend/src/pages/BoardPage.tsx` | the button + summary modal |
