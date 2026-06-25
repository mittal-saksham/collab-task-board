import type { Card } from '../types'

// Tailwind v4 only emits CSS for classes it can see as COMPLETE string literals
// at build time. So we can't build a class like `bg-${color}-100` dynamically —
// it would compile to nothing and the chip would render colorless. Instead we
// keep a static map of allowed colors → literal classes. The new-label color
// picker (in CardModal) is also driven from these keys, so you can never create
// a label whose color has no matching style.
export const LABEL_STYLES: Record<string, string> = {
  slate: 'bg-slate-100 text-slate-700',
  red: 'bg-red-100 text-red-700',
  orange: 'bg-orange-100 text-orange-700',
  amber: 'bg-amber-100 text-amber-700',
  green: 'bg-green-100 text-green-700',
  sky: 'bg-sky-100 text-sky-700',
  indigo: 'bg-indigo-100 text-indigo-700',
  violet: 'bg-violet-100 text-violet-700',
  pink: 'bg-pink-100 text-pink-700',
}

// Priority → a small colored dot. Order goes most-urgent (red) to least (slate).
const PRIORITY_DOT: Record<string, string> = {
  highest: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-amber-400',
  low: 'bg-sky-400',
  lowest: 'bg-slate-300',
}

// First two letters of the email, e.g. "saksham@…" → "SA". A cheap stand-in for
// an avatar image.
function initials(email: string): string {
  return email.slice(0, 2).toUpperCase()
}

// Turn an ISO date ("2026-07-01") into a short label + an overdue flag. We append
// T00:00:00 so it's parsed in LOCAL time (a bare date string is treated as UTC,
// which can shift the day depending on timezone).
function formatDue(due: string): { label: string; overdue: boolean } {
  const d = new Date(`${due}T00:00:00`)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return {
    label: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    overdue: d < today,
  }
}

// The metadata row(s) shown on every card: label chips on top, then a footer with
// the priority dot, an optional due-date chip, and the assignee avatar (pushed to
// the right with ml-auto).
export function CardBadges({ card }: { card: Card }) {
  const due = card.due_date ? formatDue(card.due_date) : null

  return (
    <>
      {card.labels.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {card.labels.map((l) => (
            <span
              key={l.id}
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                LABEL_STYLES[l.color] ?? LABEL_STYLES.slate
              }`}
            >
              {l.name}
            </span>
          ))}
        </div>
      )}

      <div className="mt-1.5 flex items-center gap-2">
        <span
          title={`Priority: ${card.priority}`}
          className={`h-2 w-2 flex-shrink-0 rounded-full ${
            PRIORITY_DOT[card.priority] ?? PRIORITY_DOT.medium
          }`}
        />
        {due && (
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
              due.overdue ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
            }`}
          >
            {due.label}
          </span>
        )}
        {card.assignee && (
          <span
            title={card.assignee.email}
            className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500 text-[9px] font-semibold text-white"
          >
            {initials(card.assignee.email)}
          </span>
        )}
      </div>
    </>
  )
}
