import { useState, type FormEvent } from 'react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { List } from '../types'
import { SortableCard } from './SortableCard'

interface Props {
  list: List
  onAddCard: (title: string) => void
  onDeleteCard: (cardId: number) => void
  onDeleteList: () => void
  onOpenCard: (cardId: number) => void
  onSetWipLimit: (limit: number | null) => void
}

// One board column. It's a droppable area (so you can drop onto an empty column)
// and wraps its cards in a SortableContext so they can be reordered by dragging.
export function Column({
  list,
  onAddCard,
  onDeleteCard,
  onDeleteList,
  onOpenCard,
  onSetWipLimit,
}: Props) {
  const { setNodeRef } = useDroppable({ id: `list-${list.id}` })
  const [title, setTitle] = useState('')
  const [editingWip, setEditingWip] = useState(false)
  const cardIds = list.cards.map((c) => `card-${c.id}`)

  // WIP limit is DISPLAY-ONLY: we show count (and "/ limit" if set) and turn the
  // badge red when over — but nothing here blocks a drop.
  const count = list.cards.length
  const over = list.wip_limit != null && count > list.wip_limit

  function submit(e: FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) return
    onAddCard(t)
    setTitle('')
  }

  function commitWip(value: string) {
    const n = parseInt(value, 10)
    // A valid limit is ≥ 1; anything else (empty, 0, NaN) clears it (null).
    onSetWipLimit(Number.isFinite(n) && n >= 1 ? n : null)
    setEditingWip(false)
  }

  return (
    <div className="flex w-72 flex-shrink-0 flex-col rounded-lg bg-slate-100 p-2">
      <div className="mb-2 flex items-center gap-2 px-1">
        <h3 className="text-sm font-semibold text-slate-700">{list.title}</h3>

        {/* WIP count / limit — click to edit the limit inline */}
        {editingWip ? (
          <input
            type="number"
            min={1}
            autoFocus
            defaultValue={list.wip_limit ?? ''}
            onBlur={(e) => commitWip(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur()
              else if (e.key === 'Escape') setEditingWip(false)
            }}
            placeholder="limit"
            className="w-16 rounded border border-slate-300 px-1 py-0.5 text-xs outline-none focus:border-indigo-400"
          />
        ) : (
          <button
            onClick={() => setEditingWip(true)}
            title="Set WIP limit"
            className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
              over
                ? 'bg-red-100 text-red-700'
                : 'bg-slate-200 text-slate-500 hover:bg-slate-300'
            }`}
          >
            {count}
            {list.wip_limit != null ? ` / ${list.wip_limit}` : ''}
          </button>
        )}

        <button
          onClick={onDeleteList}
          title="Delete list"
          className="ml-auto text-xs text-slate-400 hover:text-red-500"
        >
          ×
        </button>
      </div>

      <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
        {/* min-height keeps an empty column droppable */}
        <div ref={setNodeRef} className="flex min-h-2 flex-col gap-2">
          {list.cards.map((c) => (
            <SortableCard
              key={c.id}
              card={c}
              onDelete={() => onDeleteCard(c.id)}
              onOpen={() => onOpenCard(c.id)}
            />
          ))}
        </div>
      </SortableContext>

      <form onSubmit={submit} className="mt-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="+ Add a card"
          className="w-full rounded-md border border-transparent bg-transparent px-2 py-1 text-sm placeholder-slate-400 outline-none hover:border-slate-300 focus:border-indigo-400 focus:bg-white"
        />
      </form>
    </div>
  )
}
