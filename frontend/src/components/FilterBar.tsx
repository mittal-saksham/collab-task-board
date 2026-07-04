import { useLabels, useMembers } from '../hooks'
import { EMPTY_FILTERS, filtersActive, type Filters } from '../lib/filters'
import { ISSUE_TYPES, PRIORITIES } from './CardBadges'

const selectClass =
  'rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 outline-none focus:border-indigo-400'

// The board's filter/search bar (G4). Self-contained: it pulls the board's
// members and labels itself to populate the dropdowns. It owns no filter state —
// the parent (BoardPage) does; this just renders controls and reports changes.
export function FilterBar({
  boardId,
  filters,
  onChange,
  matchCount,
  totalCount,
}: {
  boardId: number
  filters: Filters
  onChange: (next: Filters) => void
  matchCount: number
  totalCount: number
}) {
  const { data: members = [] } = useMembers(boardId)
  const { data: labels = [] } = useLabels(boardId)
  const active = filtersActive(filters)

  // Patch one field, keep the rest.
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-4 py-2">
      <input
        value={filters.text}
        onChange={(e) => set({ text: e.target.value })}
        placeholder="Search cards…"
        className="w-48 rounded-md border border-slate-300 px-2 py-1 text-xs outline-none focus:border-indigo-400"
      />

      <select
        value={filters.assignee}
        onChange={(e) => set({ assignee: e.target.value })}
        className={selectClass}
      >
        <option value="any">Any assignee</option>
        <option value="unassigned">Unassigned</option>
        {members.map((m) => (
          <option key={m.user_id} value={String(m.user_id)}>
            {m.email}
          </option>
        ))}
      </select>

      <select
        value={filters.priority}
        onChange={(e) => set({ priority: e.target.value })}
        className={`${selectClass} capitalize`}
      >
        <option value="any">Any priority</option>
        {PRIORITIES.map((p) => (
          <option key={p} value={p} className="capitalize">
            {p}
          </option>
        ))}
      </select>

      <select
        value={filters.issueType}
        onChange={(e) => set({ issueType: e.target.value })}
        className={`${selectClass} capitalize`}
      >
        <option value="any">Any type</option>
        {ISSUE_TYPES.map((t) => (
          <option key={t} value={t} className="capitalize">
            {t}
          </option>
        ))}
      </select>

      <select
        value={filters.label}
        onChange={(e) => set({ label: e.target.value })}
        className={selectClass}
      >
        <option value="any">Any label</option>
        {labels.map((l) => (
          <option key={l.id} value={String(l.id)}>
            {l.name}
          </option>
        ))}
      </select>

      {active && (
        <>
          <button
            onClick={() => onChange(EMPTY_FILTERS)}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            Clear
          </button>
          <span className="text-xs text-slate-400">
            Showing {matchCount} of {totalCount}
          </span>
        </>
      )}
    </div>
  )
}
