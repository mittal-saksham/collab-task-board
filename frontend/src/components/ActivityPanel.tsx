import { useActivities } from '../hooks'
import { initials, timeAgo } from '../lib/time'

// A dropdown panel showing the board's recent activity feed (newest first).
// Read-only — entries are created server-side as a side-effect of other actions.
export function ActivityPanel({
  boardId,
  onClose,
}: {
  boardId: number
  onClose: () => void
}) {
  const { data: activities = [], isLoading } = useActivities(boardId)

  return (
    <div className="absolute right-0 top-10 z-10 w-80 rounded-lg border border-slate-200 bg-white p-4 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Activity</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ×
        </button>
      </div>

      <ul className="max-h-96 space-y-3 overflow-y-auto">
        {isLoading && <li className="text-sm text-slate-400">Loading…</li>}
        {!isLoading && activities.length === 0 && (
          <li className="text-sm text-slate-400">No activity yet.</li>
        )}
        {activities.map((a) => (
          <li key={a.id} className="flex gap-2 text-sm">
            <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-400 text-[10px] font-semibold text-white">
              {a.actor ? initials(a.actor.email) : '–'}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-slate-700">
                <span className="font-medium">
                  {a.actor ? a.actor.email.split('@')[0] : 'someone'}
                </span>{' '}
                <span className="text-slate-500">{a.summary}</span>
              </p>
              <p className="text-[11px] text-slate-400">{timeAgo(a.created_at)}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
