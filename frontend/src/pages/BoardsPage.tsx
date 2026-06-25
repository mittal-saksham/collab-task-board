import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AppHeader } from '../components/AppHeader'
import { useBoards, useCreateBoard, useDeleteBoard } from '../hooks'

// Lists the boards you can access and lets you create/delete them.
export function BoardsPage() {
  const { data: boards, isLoading, error } = useBoards()
  const createBoard = useCreateBoard()
  const deleteBoard = useDeleteBoard()
  const [title, setTitle] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    const t = title.trim()
    if (!t) return
    createBoard.mutate(t)
    setTitle('')
  }

  return (
    <div className="min-h-full bg-slate-100">
      <AppHeader />
      <main className="mx-auto max-w-4xl p-6">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Your boards</h2>

        <form onSubmit={submit} className="mb-6 flex gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New board title"
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={createBoard.isPending}
            className="rounded-md bg-indigo-600 px-4 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Create
          </button>
        </form>

        {isLoading && <p className="text-slate-500">Loading…</p>}
        {error && <p className="text-red-600">Failed to load boards.</p>}

        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {boards?.map((b) => (
            <li key={b.id} className="group relative">
              <Link
                to={`/boards/${b.id}`}
                className="block rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200 hover:ring-indigo-300"
              >
                <span className="font-medium text-slate-800">{b.title}</span>
              </Link>
              <button
                onClick={() => deleteBoard.mutate(b.id)}
                title="Delete board"
                className="absolute right-2 top-2 text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-red-500"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        {boards?.length === 0 && !isLoading && (
          <p className="text-slate-500">No boards yet — create one above.</p>
        )}
      </main>
    </div>
  )
}
