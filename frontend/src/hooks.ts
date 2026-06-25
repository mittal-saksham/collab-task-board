// TanStack Query hooks. The pattern:
//   useQuery   -> reads + caches server data (keyed by a queryKey)
//   useMutation -> writes; on success we invalidate the relevant query so it
//                  refetches and the UI reflects the change.
//
// queryKey is how Query identifies a cache entry: ['board', 5] is "board #5".

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './lib/boards'

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

// All the mutations that change a board's contents share one invalidation:
// refetch ['board', boardId] so the column/card UI updates.
export function useBoardMutations(boardId: number) {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['board', boardId] })

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
  }
}
