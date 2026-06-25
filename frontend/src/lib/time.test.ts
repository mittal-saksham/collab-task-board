import { describe, it, expect, vi, afterEach } from 'vitest'
import { initials, timeAgo } from './time'

describe('initials', () => {
  it('takes the first two letters, uppercased', () => {
    expect(initials('saksham@example.com')).toBe('SA')
  })
})

describe('timeAgo', () => {
  // timeAgo reads Date.now(); fake the clock so "now" is deterministic.
  afterEach(() => vi.useRealTimers())
  const freezeNow = (iso: string) => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(iso))
  }
  const NOW = '2026-06-25T12:00:00Z'

  it('says "just now" under 45 seconds', () => {
    freezeNow(NOW)
    expect(timeAgo('2026-06-25T11:59:30Z')).toBe('just now')
  })
  it('reports minutes', () => {
    freezeNow(NOW)
    expect(timeAgo('2026-06-25T11:55:00Z')).toBe('5m ago')
  })
  it('reports hours', () => {
    freezeNow(NOW)
    expect(timeAgo('2026-06-25T09:00:00Z')).toBe('3h ago')
  })
  it('reports days', () => {
    freezeNow(NOW)
    expect(timeAgo('2026-06-23T12:00:00Z')).toBe('2d ago')
  })
  it('falls back to a date past a week', () => {
    freezeNow(NOW)
    const label = timeAgo('2026-06-01T12:00:00Z') // 24 days earlier
    expect(label).not.toMatch(/ago|just now/)
  })
})
