// Turn an ISO timestamp into a short relative label, e.g. "just now", "5m ago",
// "3h ago", "2d ago", then falls back to a date for anything older than a week.
export function timeAgo(iso: string): string {
  const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (secs < 45) return 'just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

// First two letters of an email, uppercased — a cheap avatar stand-in.
export function initials(email: string): string {
  return email.slice(0, 2).toUpperCase()
}
