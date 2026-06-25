// REST calls for boards, lists, cards, and members. Each is a thin typed wrapper
// over apiFetch (which adds the JWT + base URL). The React Query hooks in
// src/hooks.ts call these.

import { apiFetch } from './api'
import type { Board, BoardDetail, Card, List, Member } from '../types'

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
export const moveList = (id: number, afterId: number | null) =>
  apiFetch<List>(`/lists/${id}/move`, {
    method: 'PATCH',
    body: JSON.stringify({ after_id: afterId }),
  })

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

// --- Optional: LLM summary ---
export const summarizeBoard = (boardId: number) =>
  apiFetch<{ summary: string }>(`/boards/${boardId}/summarize`, { method: 'POST' })

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
