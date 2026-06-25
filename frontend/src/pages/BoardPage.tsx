import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { AppHeader } from '../components/AppHeader'
import { Column } from '../components/Column'
import { useBoard, useBoardMutations } from '../hooks'

// A single board: its columns (lists) laid out left-to-right, each with its cards.
export function BoardPage() {
  const { boardId } = useParams()
  const id = Number(boardId)
  const { data: board, isLoading, error } = useBoard(id)
  const m = useBoardMutations(id)
  const [listTitle, setListTitle] = useState('')

  function addList(e: FormEvent) {
    e.preventDefault()
    const t = listTitle.trim()
    if (!t) return
    m.createList.mutate(t)
    setListTitle('')
  }

  return (
    <div className="flex min-h-full flex-col bg-slate-50">
      <AppHeader>
        {board && <span className="text-slate-400">/ {board.title}</span>}
      </AppHeader>

      <main className="flex-1 overflow-x-auto p-4">
        {isLoading && <p className="text-slate-500">Loading…</p>}
        {error && <p className="text-red-600">Couldn't load this board.</p>}

        {board && (
          <div className="flex items-start gap-3">
            {board.lists.map((list) => (
              <Column
                key={list.id}
                list={list}
                onAddCard={(title) => m.createCard.mutate({ listId: list.id, title })}
                onDeleteCard={(cardId) => m.deleteCard.mutate(cardId)}
                onDeleteList={() => m.deleteList.mutate(list.id)}
              />
            ))}

            <form onSubmit={addList} className="w-72 flex-shrink-0">
              <input
                value={listTitle}
                onChange={(e) => setListTitle(e.target.value)}
                placeholder="+ Add a list"
                className="w-full rounded-lg border border-dashed border-slate-300 bg-white/50 px-3 py-2 text-sm placeholder-slate-400 outline-none focus:border-indigo-400"
              />
            </form>
          </div>
        )}
      </main>
    </div>
  )
}
