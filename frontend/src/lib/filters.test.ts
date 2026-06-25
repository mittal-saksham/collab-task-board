import { describe, it, expect } from 'vitest'
import { EMPTY_FILTERS, cardMatches, filtersActive, type Filters } from './filters'
import type { Card } from '../types'

// A valid Card with sensible defaults; override per test.
function makeCard(overrides: Partial<Card> = {}): Card {
  return {
    id: 1,
    list_id: 1,
    title: 'Wire up drag and drop',
    description: 'use dnd-kit',
    position: 1024,
    priority: 'medium',
    due_date: null,
    issue_type: 'task',
    story_points: null,
    assignee: null,
    labels: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const f = (overrides: Partial<Filters> = {}): Filters => ({
  ...EMPTY_FILTERS,
  ...overrides,
})

describe('filtersActive', () => {
  it('is false for the empty filter state', () => {
    expect(filtersActive(EMPTY_FILTERS)).toBe(false)
  })
  it('is true once any field narrows the view', () => {
    expect(filtersActive(f({ text: 'wire' }))).toBe(true)
    expect(filtersActive(f({ assignee: 'unassigned' }))).toBe(true)
    expect(filtersActive(f({ priority: 'high' }))).toBe(true)
  })
  it('ignores whitespace-only text', () => {
    expect(filtersActive(f({ text: '   ' }))).toBe(false)
  })
})

describe('cardMatches', () => {
  it('matches everything when no filter is active', () => {
    expect(cardMatches(makeCard(), EMPTY_FILTERS)).toBe(true)
  })

  describe('text', () => {
    it('matches title case-insensitively', () => {
      expect(cardMatches(makeCard(), f({ text: 'WIRE' }))).toBe(true)
    })
    it('matches the description too', () => {
      expect(cardMatches(makeCard(), f({ text: 'dnd' }))).toBe(true)
    })
    it('fails when neither title nor description contains it', () => {
      expect(cardMatches(makeCard(), f({ text: 'nope' }))).toBe(false)
    })
    it('tolerates a null description', () => {
      expect(cardMatches(makeCard({ description: null }), f({ text: 'wire' }))).toBe(true)
    })
  })

  describe('assignee', () => {
    const assigned = makeCard({ assignee: { id: 9, email: 'a@x.com' } })
    it("'unassigned' matches only cards with no assignee", () => {
      expect(cardMatches(makeCard(), f({ assignee: 'unassigned' }))).toBe(true)
      expect(cardMatches(assigned, f({ assignee: 'unassigned' }))).toBe(false)
    })
    it('a specific id matches that user only', () => {
      expect(cardMatches(assigned, f({ assignee: '9' }))).toBe(true)
      expect(cardMatches(assigned, f({ assignee: '7' }))).toBe(false)
      expect(cardMatches(makeCard(), f({ assignee: '9' }))).toBe(false)
    })
  })

  describe('label', () => {
    const card = makeCard({ labels: [{ id: 2, name: 'backend', color: 'indigo' }] })
    it('matches when the card carries the chosen label', () => {
      expect(cardMatches(card, f({ label: '2' }))).toBe(true)
    })
    it('fails when it does not', () => {
      expect(cardMatches(card, f({ label: '3' }))).toBe(false)
      expect(cardMatches(makeCard(), f({ label: '2' }))).toBe(false)
    })
  })

  it('filters by priority and issue type', () => {
    expect(cardMatches(makeCard({ priority: 'high' }), f({ priority: 'high' }))).toBe(true)
    expect(cardMatches(makeCard({ priority: 'low' }), f({ priority: 'high' }))).toBe(false)
    expect(cardMatches(makeCard({ issue_type: 'bug' }), f({ issueType: 'bug' }))).toBe(true)
    expect(cardMatches(makeCard({ issue_type: 'task' }), f({ issueType: 'bug' }))).toBe(false)
  })

  it('combines filters with AND (must pass all active)', () => {
    const card = makeCard({ priority: 'high', issue_type: 'bug' })
    expect(cardMatches(card, f({ priority: 'high', issueType: 'bug' }))).toBe(true)
    // one mismatch is enough to exclude it
    expect(cardMatches(card, f({ priority: 'high', issueType: 'story' }))).toBe(false)
  })
})
