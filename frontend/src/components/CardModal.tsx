import { useState, type FormEvent, type ReactNode } from 'react'
import type { Card } from '../types'
import type { CardPatch } from '../lib/boards'
import { useBoardMutations, useLabels, useMembers } from '../hooks'
import { CommentThread } from './CommentThread'
import { LABEL_STYLES } from './CardBadges'

// The five priority levels the backend accepts (schemas/card.py Priority).
const PRIORITIES = ['highest', 'high', 'medium', 'low', 'lowest']
// A new label may only use a color we have a style for (see CardBadges).
const LABEL_COLORS = Object.keys(LABEL_STYLES)

// Small helper for a sidebar field: an uppercase label above its control.
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </span>
      {children}
    </label>
  )
}

const selectClass =
  'w-full rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm text-slate-700 outline-none transition hover:border-slate-300 focus:border-indigo-400 focus:bg-white'

// Card detail / edit modal. SELF-CONTAINED: given a card + boardId it pulls the
// board's members (assignee dropdown) and label palette itself, and writes
// through useBoardMutations. The parent keys it on card.id, so it remounts when a
// different card opens — which lets the title/description draft state initialize
// ONCE without a useEffect re-sync (a background refetch can't clobber typing).
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

  const [title, setTitle] = useState(card.title)
  const [description, setDescription] = useState(card.description ?? '')
  const [newLabel, setNewLabel] = useState('')
  const [newColor, setNewColor] = useState(LABEL_COLORS[0])

  const patch = (p: CardPatch) => m.updateCard.mutate({ id: card.id, patch: p })

  function saveTitle() {
    const t = title.trim()
    if (!t || t === card.title) return // ignore empty (would 422) or unchanged
    patch({ title: t })
  }
  function saveDescription() {
    const d = description === '' ? null : description // empty box → clear it
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

  const attachedIds = new Set(card.labels.map((l) => l.id))

  return (
    // Backdrop: clicking outside the panel closes the modal.
    <div
      className="fixed inset-0 z-30 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-xl bg-white shadow-2xl ring-1 ring-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start gap-2 border-b border-slate-100 px-5 py-4">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={saveTitle}
            className="w-full rounded-md border border-transparent px-2 py-1 text-lg font-semibold text-slate-800 outline-none transition hover:border-slate-200 focus:border-indigo-400"
          />
          <button
            onClick={onClose}
            title="Close"
            className="rounded-md px-2 py-1 text-xl leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            ×
          </button>
        </div>

        {/* Body: main content + properties sidebar */}
        <div className="flex flex-col gap-6 p-5 sm:flex-row">
          {/* --- Main column: description + comments --- */}
          <div className="min-w-0 flex-1 space-y-6">
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Description
              </p>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onBlur={saveDescription}
                rows={4}
                placeholder="Add a more detailed description…"
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-indigo-400"
              />
            </div>

            <CommentThread cardId={card.id} boardId={boardId} />
          </div>

          {/* --- Sidebar: properties --- */}
          <aside className="space-y-4 sm:w-56 sm:flex-shrink-0">
            <Field label="Assignee">
              <select
                value={card.assignee?.id ?? ''}
                onChange={(e) =>
                  // "" (Unassigned) sends an explicit null (not undefined/""), or
                  // the backend's exclude_unset treats it as "no change".
                  patch({
                    assignee_id: e.target.value ? Number(e.target.value) : null,
                  })
                }
                className={selectClass}
              >
                <option value="">Unassigned</option>
                {members.map((mem) => (
                  <option key={mem.user_id} value={mem.user_id}>
                    {mem.email}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Priority">
              <select
                value={card.priority}
                onChange={(e) => patch({ priority: e.target.value })}
                className={`${selectClass} capitalize`}
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p} className="capitalize">
                    {p}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Due date">
              <input
                type="date"
                value={card.due_date ?? ''}
                onChange={(e) => patch({ due_date: e.target.value || null })}
                className={selectClass}
              />
            </Field>

            <div>
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Labels
              </p>
              <div className="flex flex-wrap gap-1.5">
                {labels.length === 0 && (
                  <span className="text-xs text-slate-400">No labels yet.</span>
                )}
                {labels.map((l) => {
                  const on = attachedIds.has(l.id)
                  return (
                    // chip = toggle (name) + delete (×)
                    <span
                      key={l.id}
                      className={`inline-flex items-center rounded text-xs font-medium transition ${
                        LABEL_STYLES[l.color] ?? LABEL_STYLES.slate
                      } ${on ? 'ring-2 ring-slate-400' : 'opacity-40 hover:opacity-100'}`}
                    >
                      <button
                        onClick={() =>
                          on
                            ? m.detachLabel.mutate({ cardId: card.id, labelId: l.id })
                            : m.attachLabel.mutate({ cardId: card.id, labelId: l.id })
                        }
                        title={on ? 'Remove from this card' : 'Add to this card'}
                        className="py-0.5 pl-2 pr-1"
                      >
                        {l.name}
                      </button>
                      <button
                        onClick={() => m.deleteLabel.mutate(l.id)}
                        title="Delete label from board"
                        className="py-0.5 pl-0.5 pr-1.5 opacity-60 hover:opacity-100"
                      >
                        ×
                      </button>
                    </span>
                  )
                })}
              </div>

              {/* Create-label form: name + a color from our allowed palette. */}
              <form onSubmit={addLabel} className="mt-2 space-y-2">
                <input
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="New label"
                  maxLength={50}
                  className="w-full rounded-md border border-slate-200 px-2 py-1 text-sm outline-none focus:border-indigo-400"
                />
                <div className="flex gap-2">
                  <select
                    value={newColor}
                    onChange={(e) => setNewColor(e.target.value)}
                    className={`${selectClass} flex-1 capitalize`}
                  >
                    {LABEL_COLORS.map((c) => (
                      <option key={c} value={c} className="capitalize">
                        {c}
                      </option>
                    ))}
                  </select>
                  <button
                    type="submit"
                    className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
                  >
                    Add
                  </button>
                </div>
              </form>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
