import { useState, type FormEvent } from 'react'
import type { List } from '../types'
import { CardItem } from './CardItem'

interface Props {
  list: List
  onAddCard: (title: string) => void
  onDeleteCard: (cardId: number) => void
  onDeleteList: () => void
}

// One board column: its title, its cards (already ordered by the backend), and
// an inline "add a card" input.
export function Column({ list, onAddCard, onDeleteCard, onDeleteList }: Props) {
  const [title, setTitle] = useState('')

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

      <div className="flex flex-col gap-2">
        {list.cards.map((c) => (
          <CardItem key={c.id} card={c} onDelete={() => onDeleteCard(c.id)} />
        ))}
      </div>

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
