import { type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

// Shared top bar: app name (links home), optional middle content, user + logout.
export function AppHeader({ children }: { children?: ReactNode }) {
  const { user, logout } = useAuth()
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
      <div className="flex items-center gap-3">
        <Link to="/boards" className="text-lg font-semibold text-slate-800">
          Task Board
        </Link>
        {children}
      </div>
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
  )
}
