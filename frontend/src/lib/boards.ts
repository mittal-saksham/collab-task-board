// REST calls for boards, lists, cards, and members. Each is a thin typed wrapper
// over apiFetch (which adds the JWT + base URL). The React Query hooks in
// src/hooks.ts call these.

import { apiFetch } from './api'
import type {
  Activity,
  Board,
  BoardDetail,
  Card,
  Comment,
  Label,
  List,
  Member,
} from '../types'

// --- Boards ---
export const getBoards = () => apiFetch<Board[]>('/boards')
export const getBoard = (id: number) => apiFetch<BoardDetail>(`/boards/${id}`)
export const createBoard = (title: string) =>
  apiFetch<Board>('/boards', { method: 'POST', body: JSON.stringify({ title }) })
export const deleteBoard = (id: number) =>
  apiFetch<void>(`/boards/${id}`, { method: 'DELETE' })

// --- Lists ---
export const createList = (boardId: number, title: string) =>
  apiFetch<List>(`/boards/${boardId}/lists`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
export const deleteList = (id: number) =>
  apiFetch<void>(`/lists/${id}`, { method: 'DELETE' })

// --- Cards ---
export const createCard = (listId: number, title: string) =>
  apiFetch<Card>(`/lists/${listId}/cards`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
export const deleteCard = (id: number) =>
  apiFetch<void>(`/cards/${id}`, { method: 'DELETE' })
export const moveCard = (id: number, listId: number, afterId: number | null) =>
  apiFetch<Card>(`/cards/${id}/move`, {
    method: 'PATCH',
    body: JSON.stringify({ list_id: listId, after_id: afterId }),
  })

// PATCH a card's editable fields. Every field is OPTIONAL, but note the null vs
// undefined distinction: the backend uses `exclude_unset`, so only keys actually
// PRESENT in the JSON are applied. To CLEAR a field you must send an explicit
// `null` (e.g. assignee_id: null to unassign) — leaving the key off means "no
// change". JSON.stringify drops `undefined` keys but keeps `null`, so callers
// pass null (not undefined/"") to clear.
export interface CardPatch {
  title?: string
  description?: string | null
  priority?: string
  due_date?: string | null
  assignee_id?: number | null
  issue_type?: string
  story_points?: number | null
}
export const updateCard = (id: number, patch: CardPatch) =>
  apiFetch<Card>(`/cards/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })

// Edit a list's title and/or WIP limit. Same null-to-clear semantics as cards:
// `wip_limit: null` removes the limit; omitting a key leaves it unchanged.
export interface ListPatch {
  title?: string
  wip_limit?: number | null
}
export const updateList = (id: number, patch: ListPatch) =>
  apiFetch<List>(`/lists/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })

// --- Labels (board-scoped tags) ---
export const getLabels = (boardId: number) =>
  apiFetch<Label[]>(`/boards/${boardId}/labels`)
export const createLabel = (boardId: number, name: string, color: string) =>
  apiFetch<Label>(`/boards/${boardId}/labels`, {
    method: 'POST',
    body: JSON.stringify({ name, color }),
  })
export const deleteLabel = (id: number) =>
  apiFetch<void>(`/labels/${id}`, { method: 'DELETE' })
// Attach/detach return the UPDATED card (with its new labels array).
export const attachLabel = (cardId: number, labelId: number) =>
  apiFetch<Card>(`/cards/${cardId}/labels/${labelId}`, { method: 'PUT' })
export const detachLabel = (cardId: number, labelId: number) =>
  apiFetch<Card>(`/cards/${cardId}/labels/${labelId}`, { method: 'DELETE' })

// --- Optional: LLM summary ---
export const summarizeBoard = (boardId: number) =>
  apiFetch<{ summary: string }>(`/boards/${boardId}/summarize`, { method: 'POST' })

// --- Comments (a card's discussion thread) ---
export const getComments = (cardId: number) =>
  apiFetch<Comment[]>(`/cards/${cardId}/comments`)
export const createComment = (cardId: number, body: string) =>
  apiFetch<Comment>(`/cards/${cardId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  })
export const deleteComment = (id: number) =>
  apiFetch<void>(`/comments/${id}`, { method: 'DELETE' })

// --- Activity feed (board-level, read-only) ---
export const getActivities = (boardId: number) =>
  apiFetch<Activity[]>(`/boards/${boardId}/activities`)

// --- Members ---
export const getMembers = (boardId: number) =>
  apiFetch<Member[]>(`/boards/${boardId}/members`)
export const addMember = (boardId: number, email: string) =>
  apiFetch<Member>(`/boards/${boardId}/members`, {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
export const removeMember = (boardId: number, userId: number) =>
  apiFetch<void>(`/boards/${boardId}/members/${userId}`, { method: 'DELETE' })
