import { useAuth } from '../auth/AuthContext'

// Placeholder for now — the real board list (with TanStack Query) arrives in the
// next sub-batch. This proves the protected route + auth context work.
export function BoardsPage() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-full bg-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <h1 className="text-lg font-semibold text-slate-800">Task Board</h1>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-500">{user?.email}</span>
          <button
            onClick={logout}
            className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="p-6">
        <p className="text-slate-600">
          You're signed in. The board list and the board view come next.
        </p>
      </main>
    </div>
  )
}
