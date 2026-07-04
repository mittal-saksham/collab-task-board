// TanStack Query hooks. The pattern:
//   useQuery   -> reads + caches server data (keyed by a queryKey)
//   useMutation -> writes; on success we invalidate the relevant query so it
//                  refetches and the UI reflects the change.
//
// queryKey is how Query identifies a cache entry: ['board', 5] is "board #5".

import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './lib/boards'
import { WS_BASE, getToken, getWsTicket } from './lib/api'
import type { BoardDetail } from './types'

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
//
// The socket RECONNECTS with exponential backoff when it drops (backend
// redeploy, laptop sleep, proxy idle timeout) — without this, live updates
// silently died for the rest of the session. On every (re)connect we refetch,
// since events may have been missed while disconnected.
export function useBoardLiveUpdates(boardId: number) {
  const qc = useQueryClient()
  useEffect(() => {
    if (!boardId) return

    let ws: WebSocket | null = null
    let unmounted = false
    let attempt = 0
    let retryTimer: number | undefined

    // Refetch everything this board view shows. Cheapest way to stay live:
    // let each query decide if its data actually changed. (Comments are keyed
    // per-card and the event doesn't say which, so invalidate all of them —
    // only the open card's thread is actually mounted.)
    const refetchAll = () => {
      qc.invalidateQueries({ queryKey: ['board', boardId] })
      qc.invalidateQueries({ queryKey: ['members', boardId] })
      qc.invalidateQueries({ queryKey: ['labels', boardId] })
      qc.invalidateQueries({ queryKey: ['activities', boardId] })
      qc.invalidateQueries({ queryKey: ['comments'] })
    }

    const scheduleRetry = () => {
      if (unmounted) return
      // 1s, 2s, 4s, ... capped at 30s between attempts.
      const delay = Math.min(30_000, 1000 * 2 ** attempt++)
      retryTimer = window.setTimeout(connect, delay)
    }

    const connect = async () => {
      if (!getToken()) return // logged out — nothing to subscribe to

      // Trade the JWT for a single-use ~60s ticket (the JWT itself must never
      // ride in the WS URL — URLs land in server logs). A fresh ticket is
      // fetched on every attempt: they're consumed on use, so reconnects
      // can't reuse the old one.
      let ticket: string
      try {
        ticket = await getWsTicket()
      } catch {
        // Backend unreachable (or 401, which clears the token and stops the
        // next attempt via the guard above). Retry with backoff.
        scheduleRetry()
        return
      }
      if (unmounted) return

      ws = new WebSocket(`${WS_BASE}/ws/boards/${boardId}?ticket=${ticket}`)
      ws.onopen = () => {
        attempt = 0 // healthy again: reset the backoff
        refetchAll() // catch up on anything missed while disconnected
      }
      ws.onmessage = refetchAll
      ws.onclose = scheduleRetry
    }
    void connect()

    // Leaving the board / unmounting: stop reconnecting and close the socket.
    return () => {
      unmounted = true
      window.clearTimeout(retryTimer)
      ws?.close()
    }
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
    // OPTIMISTIC delete: remove the card from the cached board immediately, before
    // the server responds, so it disappears instantly (no waiting on the round-trip
    // — especially noticeable on a slow/cold-started server). The TanStack pattern:
    //   onMutate  → cancel in-flight refetches, snapshot the cache, apply the change
    //   onError   → roll back to the snapshot (the delete failed, restore the card)
    //   onSettled → invalidate so we re-sync with the server's truth either way
    deleteCard: useMutation({
      mutationFn: (id: number) => api.deleteCard(id),
      onMutate: async (id: number) => {
        await qc.cancelQueries({ queryKey: ['board', boardId] })
        const previous = qc.getQueryData<BoardDetail>(['board', boardId])
        qc.setQueryData<BoardDetail>(['board', boardId], (old) =>
          old
            ? {
                ...old,
                lists: old.lists.map((l) => ({
                  ...l,
                  cards: l.cards.filter((c) => c.id !== id),
                })),
              }
            : old,
        )
        return { previous } // becomes `context` in onError
      },
      onError: (_err, _id, context) => {
        // Put the card back if the server rejected the delete.
        if (context?.previous) {
          qc.setQueryData(['board', boardId], context.previous)
        }
      },
      onSettled: invalidate,
    }),
    // OPTIMISTIC move (same shape as deleteCard): write the move into the cache
    // immediately and cancel in-flight refetches. Cancelling matters here — a
    // refetch started BEFORE the drag (e.g. triggered by a teammate's WS event)
    // would resolve with pre-drag data and visibly snap the card back. onError
    // rolls back; onSettled re-syncs with the server's truth either way, so a
    // failed move can never leave the board permanently out of sync.
    moveCard: useMutation({
      mutationFn: (v: { id: number; listId: number; afterId: number | null }) =>
        api.moveCard(v.id, v.listId, v.afterId),
      onMutate: async (v) => {
        await qc.cancelQueries({ queryKey: ['board', boardId] })
        const previous = qc.getQueryData<BoardDetail>(['board', boardId])
        qc.setQueryData<BoardDetail>(['board', boardId], (old) => {
          if (!old) return old
          const moved = old.lists
            .flatMap((l) => l.cards)
            .find((c) => c.id === v.id)
          if (!moved) return old
          return {
            ...old,
            lists: old.lists.map((l) => {
              const cards = l.cards.filter((c) => c.id !== v.id)
              if (l.id !== v.listId) return { ...l, cards }
              // Insert right after afterId (null = front of the list).
              const at =
                v.afterId === null
                  ? 0
                  : cards.findIndex((c) => c.id === v.afterId) + 1
              cards.splice(at, 0, { ...moved, list_id: v.listId })
              return { ...l, cards }
            }),
          }
        })
        return { previous }
      },
      onError: (_err, _v, context) => {
        if (context?.previous) {
          qc.setQueryData(['board', boardId], context.previous)
        }
      },
      onSettled: invalidate,
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
