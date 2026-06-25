import { useState, type FormEvent } from 'react'
import type { Card } from '../types'
import type { CardPatch } from '../lib/boards'
import { useBoardMutations, useLabels, useMembers } from '../hooks'
import { LABEL_STYLES } from './CardBadges'

// The five priority levels the backend accepts (schemas/card.py Priority).
const PRIORITIES = ['highest', 'high', 'medium', 'low', 'lowest']
// A new label may only use a color we have a style for (see CardBadges).
const LABEL_COLORS = Object.keys(LABEL_STYLES)

// Card detail / edit modal. It's SELF-CONTAINED: given just the card and its
// board id, it pulls the board's members (for the assignee dropdown) and label
// palette itself, and writes through useBoardMutations. The parent keys this
// component on card.id, so it remounts when a different card opens — which is why
// the title/description draft state below can safely initialize ONCE without a
// useEffect re-sync (a background refetch can't clobber what you're typing).
export function CardModal({
  card,
  boardId,
  onClose,
}: {
  card: Card
  boardId: number
  onClose: () => void
}) {
  const m = useBoardMutations(boardId)
  const { data: members = [] } = useMembers(boardId)
  const { data: labels = [] } = useLabels(boardId)

  // Draft state for the free-text fields (saved on blur). The select/date/label
  // controls below are driven straight off `card` and write immediately, so they
  // don't need local state.
  const [title, setTitle] = useState(card.title)
  const [description, setDescription] = useState(card.description ?? '')

  // New-label form.
  const [newLabel, setNewLabel] = useState('')
  const [newColor, setNewColor] = useState(LABEL_COLORS[0])

  // Tiny helper: PATCH this card with the given fields.
  const patch = (p: CardPatch) => m.updateCard.mutate({ id: card.id, patch: p })

  function saveTitle() {
    const t = title.trim()
    if (!t || t === card.title) return // ignore empty (would 422) or unchanged
    patch({ title: t })
  }

  function saveDescription() {
    // Empty box → null (clear it); otherwise the text. Skip if unchanged.
    const d = description === '' ? null : description
    if ((d ?? '') === (card.description ?? '')) return
    patch({ description: d })
  }

  function addLabel(e: FormEvent) {
    e.preventDefault()
    const name = newLabel.trim()
    if (!name) return
    m.createLabel.mutate({ name, color: newColor })
    setNewLabel('')
  }

  // Which labels are currently on this card (for the toggle chips).
  const attachedIds = new Set(card.labels.map((l) => l.id))

  return (
    // Backdrop: clicking it (outside the panel) closes the modal.
    <div
      className="fixed inset-0 z-30 flex items-start justify-center overflow-y-auto bg-black/30 p-4 sm:p-8"
      onClick={onClose}
    >
      {/* stopPropagation so clicks INSIDE the panel don't bubble to the backdrop */}
      <div
        className="w-full max-w-lg rounded-lg bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-2">
          {/* Title is an input so you can edit it inline; saves on blur. */}
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={saveTitle}
            className="w-full rounded-md border border-transparent px-2 py-1 text-lg font-semibold text-slate-800 outline-none hover:border-slate-300 focus:border-indigo-400"
          />
          <button
            onClick={onClose}
            title="Close"
            className="px-1 text-xl leading-none text-slate-400 hover:text-slate-600"
          >
            ×
          </button>
        </div>

        {/* --- Properties: assignee / priority / due date --- */}
        <div className="grid grid-cols-3 gap-3">
          <label className="text-xs font-medium text-slate-500">
            Assignee
            <select
              value={card.assignee?.id ?? ''}
              onChange={(e) =>
                // "" (Unassigned) must send an explicit null, not undefined/"",
                // or the backend's exclude_unset treats it as "no change".
                patch({
                  assignee_id: e.target.value ? Number(e.target.value) : null,
                })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-700 outline-none focus:border-indigo-400"
            >
              <option value="">Unassigned</option>
              {members.map((mem) => (
                <option key={mem.user_id} value={mem.user_id}>
                  {mem.email}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs font-medium text-slate-500">
            Priority
            <select
              value={card.priority}
              onChange={(e) => patch({ priority: e.target.value })}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm capitalize text-slate-700 outline-none focus:border-indigo-400"
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p} className="capitalize">
                  {p}
                </option>
              ))}
            </select>
          </label>

          <label className="text-xs font-medium text-slate-500">
            Due date
            <input
              type="date"
              value={card.due_date ?? ''}
              onChange={(e) =>
                // Clearing the field → null (clear the due date).
                patch({ due_date: e.target.value || null })
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-700 outline-none focus:border-indigo-400"
            />
          </label>
        </div>

        {/* --- Description --- */}
        <div className="mt-4">
          <p className="text-xs font-medium text-slate-500">Description</p>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onBlur={saveDescription}
            rows={4}
            placeholder="Add a more detailed description…"
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-700 outline-none focus:border-indigo-400"
          />
        </div>

        {/* --- Labels: toggle existing, or create new --- */}
        <div className="mt-4">
          <p className="text-xs font-medium text-slate-500">Labels</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {labels.length === 0 && (
              <span className="text-xs text-slate-400">No labels yet.</span>
            )}
            {labels.map((l) => {
              const on = attachedIds.has(l.id)
              return (
                <button
                  key={l.id}
                  onClick={() =>
                    on
                      ? m.detachLabel.mutate({ cardId: card.id, labelId: l.id })
                      : m.attachLabel.mutate({ cardId: card.id, labelId: l.id })
                  }
                  // Attached → solid + ring; not attached → faded (click to add).
                  className={`rounded px-2 py-0.5 text-xs font-medium transition ${
                    LABEL_STYLES[l.color] ?? LABEL_STYLES.slate
                  } ${on ? 'ring-2 ring-slate-400' : 'opacity-40 hover:opacity-100'}`}
                >
                  {l.name}
                </button>
              )
            })}
          </div>

          {/* Create-label form: name + a color from our allowed palette. */}
          <form onSubmit={addLabel} className="mt-2 flex items-center gap-2">
            <input
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="New label name"
              maxLength={50}
              className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm outline-none focus:border-indigo-400"
            />
            <select
              value={newColor}
              onChange={(e) => setNewColor(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm capitalize outline-none focus:border-indigo-400"
            >
              {LABEL_COLORS.map((c) => (
                <option key={c} value={c} className="capitalize">
                  {c}
                </option>
              ))}
            </select>
            <button
              type="submit"
              className="rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1 text-sm text-indigo-700 hover:bg-indigo-100"
            >
              Add
            </button>
          </form>
        </div>

        <p className="mt-4 text-right text-[11px] text-slate-400">
          Changes save automatically.
        </p>
      </div>
    </div>
  )
}
