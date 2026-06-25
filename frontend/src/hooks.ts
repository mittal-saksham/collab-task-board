// TanStack Query hooks. The pattern:
//   useQuery   -> reads + caches server data (keyed by a queryKey)
//   useMutation -> writes; on success we invalidate the relevant query so it
//                  refetches and the UI reflects the change.
//
// queryKey is how Query identifies a cache entry: ['board', 5] is "board #5".

import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './lib/boards'
import { WS_BASE, getToken } from './lib/api'

// --- Boards list ---
export function useBoards() {
  return useQuery({ queryKey: ['boards'], queryFn: api.getBoards })
}

export function useCreateBoard() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (title: string) => api.createBoard(title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boards'] }),
  })
}

export function useDeleteBoard() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteBoard(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boards'] }),
  })
}

// --- A single board (with lists + cards) ---
export function useBoard(boardId: number) {
  return useQuery({
    queryKey: ['board', boardId],
    queryFn: () => api.getBoard(boardId),
  })
}

// Subscribe to a board's WebSocket feed. Any event (card.moved, list.created,
// member.added, ...) just invalidates this board's query so it refetches — the
// simplest way to stay live. (A fancier version would patch the cache per event.)
export function useBoardLiveUpdates(boardId: number) {
  const qc = useQueryClient()
  useEffect(() => {
    const token = getToken()
    if (!token || !boardId) return

    const ws = new WebSocket(`${WS_BASE}/ws/boards/${boardId}?token=${token}`)
    ws.onmessage = () => {
      // Refetch everything this board view shows, on any event. Cheapest way to
      // stay live: let each query decide if its data actually changed.
      qc.invalidateQueries({ queryKey: ['board', boardId] })
      qc.invalidateQueries({ queryKey: ['members', boardId] })
      qc.invalidateQueries({ queryKey: ['labels', boardId] })
      qc.invalidateQueries({ queryKey: ['activities', boardId] })
      // Comments are keyed per-card; the event doesn't say which, so invalidate
      // all comment queries (only the open card's thread is actually mounted).
      qc.invalidateQueries({ queryKey: ['comments'] })
    }
    // Close the socket when leaving the board / unmounting.
    return () => ws.close()
  }, [boardId, qc])
}

// --- Optional: LLM summary (no cache; returns the summary text) ---
export function useSummarizeBoard(boardId: number) {
  return useMutation({ mutationFn: () => api.summarizeBoard(boardId) })
}

// --- Labels (a board's tag palette) ---
export function useLabels(boardId: number) {
  return useQuery({
    queryKey: ['labels', boardId],
    queryFn: () => api.getLabels(boardId),
  })
}

// --- Comments (a card's thread) ---
export function useComments(cardId: number) {
  return useQuery({
    queryKey: ['comments', cardId],
    queryFn: () => api.getComments(cardId),
  })
}

// --- Activity feed (board-level) ---
export function useActivities(boardId: number) {
  return useQuery({
    queryKey: ['activities', boardId],
    queryFn: () => api.getActivities(boardId),
  })
}

// --- Members ---
export function useMembers(boardId: number) {
  return useQuery({
    queryKey: ['members', boardId],
    queryFn: () => api.getMembers(boardId),
  })
}

export function useAddMember(boardId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => api.addMember(boardId, email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members', boardId] }),
  })
}

export function useRemoveMember(boardId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: number) => api.removeMember(boardId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['members', boardId] }),
  })
}

// All the mutations that change a board's contents share one invalidation:
// refetch ['board', boardId] so the column/card UI updates.
export function useBoardMutations(boardId: number) {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['board', boardId] })
  // Creating/deleting a label changes the board's PALETTE, so those also refetch
  // the ['labels', boardId] query (attach/detach only change a card → board query).
  const invalidateLabels = () =>
    qc.invalidateQueries({ queryKey: ['labels', boardId] })

  return {
    createList: useMutation({
      mutationFn: (title: string) => api.createList(boardId, title),
      onSuccess: invalidate,
    }),
    deleteList: useMutation({
      mutationFn: (id: number) => api.deleteList(id),
      onSuccess: invalidate,
    }),
    moveList: useMutation({
      mutationFn: (v: { id: number; afterId: number | null }) =>
        api.moveList(v.id, v.afterId),
      onSuccess: invalidate,
    }),
    // Edit a list's title / WIP limit.
    updateList: useMutation({
      mutationFn: (v: { id: number; patch: api.ListPatch }) =>
        api.updateList(v.id, v.patch),
      onSuccess: invalidate,
    }),
    createCard: useMutation({
      mutationFn: (v: { listId: number; title: string }) =>
        api.createCard(v.listId, v.title),
      onSuccess: invalidate,
    }),
    deleteCard: useMutation({
      mutationFn: (id: number) => api.deleteCard(id),
      onSuccess: invalidate,
    }),
    moveCard: useMutation({
      mutationFn: (v: { id: number; listId: number; afterId: number | null }) =>
        api.moveCard(v.id, v.listId, v.afterId),
      onSuccess: invalidate,
    }),
    // Edit a card's fields (title/description/priority/due_date/assignee_id).
    updateCard: useMutation({
      mutationFn: (v: { id: number; patch: api.CardPatch }) =>
        api.updateCard(v.id, v.patch),
      onSuccess: invalidate,
    }),
    // Label palette management.
    createLabel: useMutation({
      mutationFn: (v: { name: string; color: string }) =>
        api.createLabel(boardId, v.name, v.color),
      onSuccess: () => {
        invalidate()
        invalidateLabels()
      },
    }),
    deleteLabel: useMutation({
      mutationFn: (id: number) => api.deleteLabel(id),
      onSuccess: () => {
        invalidate()
        invalidateLabels()
      },
    }),
    // Attach/detach a label on a card.
    attachLabel: useMutation({
      mutationFn: (v: { cardId: number; labelId: number }) =>
        api.attachLabel(v.cardId, v.labelId),
      onSuccess: invalidate,
    }),
    detachLabel: useMutation({
      mutationFn: (v: { cardId: number; labelId: number }) =>
        api.detachLabel(v.cardId, v.labelId),
      onSuccess: invalidate,
    }),
    // Comments. We pass cardId through the mutation variables so onSuccess knows
    // which card's thread (and the board's activity feed) to refetch.
    createComment: useMutation({
      mutationFn: (v: { cardId: number; body: string }) =>
        api.createComment(v.cardId, v.body),
      onSuccess: (_data, v) => {
        qc.invalidateQueries({ queryKey: ['comments', v.cardId] })
        qc.invalidateQueries({ queryKey: ['activities', boardId] })
      },
    }),
    deleteComment: useMutation({
      mutationFn: (v: { cardId: number; commentId: number }) =>
        api.deleteComment(v.commentId),
      onSuccess: (_data, v) =>
        qc.invalidateQueries({ queryKey: ['comments', v.cardId] }),
    }),
  }
}
