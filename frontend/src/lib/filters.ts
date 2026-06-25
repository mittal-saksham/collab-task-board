// Client-side board filtering (G4). All filtering happens in the browser on the
// board data we already loaded — no extra API calls. A card is shown only if it
// matches EVERY active filter (logical AND).

import type { Card } from '../types'

export interface Filters {
  text: string // free-text match on title + description
  assignee: string // 'any' | 'unassigned' | a user id as a string
  label: string // 'any' | a label id as a string
  priority: string // 'any' | a priority value
  issueType: string // 'any' | 'task' | 'bug' | 'story'
}

// The "nothing selected" state. Selects use 'any' (and 'unassigned' as a special
// assignee value) so the value is always a string — easy to drive a <select>.
export const EMPTY_FILTERS: Filters = {
  text: '',
  assignee: 'any',
  label: 'any',
  priority: 'any',
  issueType: 'any',
}

// Is any filter actually narrowing the view? (Used to decide whether to filter at
// all, and to show the "Clear" button + "showing X of Y" count.)
export function filtersActive(f: Filters): boolean {
  return (
    f.text.trim() !== '' ||
    f.assignee !== 'any' ||
    f.label !== 'any' ||
    f.priority !== 'any' ||
    f.issueType !== 'any'
  )
}

// Does this card pass all active filters?
export function cardMatches(card: Card, f: Filters): boolean {
  // Text: case-insensitive substring of title or description.
  const q = f.text.trim().toLowerCase()
  if (q) {
    const hay = `${card.title} ${card.description ?? ''}`.toLowerCase()
    if (!hay.includes(q)) return false
  }
  // Assignee: 'unassigned' wants a null assignee; a numeric id wants that user.
  if (f.assignee === 'unassigned') {
    if (card.assignee) return false
  } else if (f.assignee !== 'any') {
    if (card.assignee?.id !== Number(f.assignee)) return false
  }
  // Label: the card must carry the chosen label.
  if (f.label !== 'any' && !card.labels.some((l) => l.id === Number(f.label))) {
    return false
  }
  if (f.priority !== 'any' && card.priority !== f.priority) return false
  if (f.issueType !== 'any' && card.issue_type !== f.issueType) return false
  return true
}
