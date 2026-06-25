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
}

// One board column. It's a droppable area (so you can drop onto an empty column)
// and wraps its cards in a SortableContext so they can be reordered by dragging.
export function Column({ list, onAddCard, onDeleteCard, onDeleteList }: Props) {
  const { setNodeRef } = useDroppable({ id: `list-${list.id}` })
  const [title, setTitle] = useState('')
  const cardIds = list.cards.map((c) => `card-${c.id}`)

  function submit(e: FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) return
    onAddCard(t)
    setTitle('')
  }

  return (
    <div className="flex w-72 flex-shrink-0 flex-col rounded-lg bg-slate-100 p-2">
      <div className="mb-2 flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold text-slate-700">{list.title}</h3>
        <button
          onClick={onDeleteList}
          title="Delete list"
          className="text-xs text-slate-400 hover:text-red-500"
        >
          ×
        </button>
      </div>

      <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
        {/* min-height keeps an empty column droppable */}
        <div ref={setNodeRef} className="flex min-h-2 flex-col gap-2">
          {list.cards.map((c) => (
            <SortableCard key={c.id} card={c} onDelete={() => onDeleteCard(c.id)} />
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
