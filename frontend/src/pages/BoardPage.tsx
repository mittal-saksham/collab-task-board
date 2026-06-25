import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { AppHeader } from '../components/AppHeader'
import { Column } from '../components/Column'
import { CardItem } from '../components/CardItem'
import { CardModal } from '../components/CardModal'
import { MembersPanel } from '../components/MembersPanel'
import {
  useBoard,
  useBoardLiveUpdates,
  useBoardMutations,
  useSummarizeBoard,
} from '../hooks'
import type { Card, List } from '../types'

// dnd-kit ids look like "card-12" / "list-3"; pull the numeric id back out.
const numId = (prefixed: string) => Number(prefixed.split('-')[1])

export function BoardPage() {
  const { boardId } = useParams()
  const id = Number(boardId)
  const { data: board, isLoading, error } = useBoard(id)
  useBoardLiveUpdates(id) // live: refetch this board when anyone changes it
  const m = useBoardMutations(id)
  const [listTitle, setListTitle] = useState('')

  // Local mirror of the lists so a drag can update the UI instantly. It re-syncs
  // whenever the server data changes (initial load + after a move refetch).
  const [lists, setLists] = useState<List[]>([])
  useEffect(() => {
    if (board) setLists(board.lists)
  }, [board])

  const [showMembers, setShowMembers] = useState(false)
  const [summaryOpen, setSummaryOpen] = useState(false)
  // Which card's detail modal is open (by id). We look the card itself up from
  // `lists` on each render so the modal always shows the latest server data — and
  // if that card gets deleted, the lookup returns null and the modal closes.
  const [openCardId, setOpenCardId] = useState<number | null>(null)
  const openCard =
    openCardId == null
      ? null
      : lists.flatMap((l) => l.cards).find((c) => c.id === openCardId) ?? null
  const summarize = useSummarizeBoard(id)
  const [activeCard, setActiveCard] = useState<Card | null>(null)
  // Require a 5px drag before activating, so plain clicks (e.g. the × button) work.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  )

  function findCard(cardId: number): { card: Card; list: List } | null {
    for (const l of lists) {
      const card = l.cards.find((c) => c.id === cardId)
      if (card) return { card, list: l }
    }
    return null
  }

  function onDragStart(e: DragStartEvent) {
    setActiveCard(findCard(numId(String(e.active.id)))?.card ?? null)
  }

  function onDragEnd(e: DragEndEvent) {
    setActiveCard(null)
    const { active, over } = e
    if (!over) return

    const activeId = numId(String(active.id))
    const source = findCard(activeId)
    if (!source) return

    // Resolve the target list and the card we dropped onto (if any).
    const overId = String(over.id)
    let targetList: List | undefined
    let overCardId: number | null = null
    if (overId.startsWith('list-')) {
      targetList = lists.find((l) => l.id === numId(overId)) // dropped on a column
    } else {
      const overCard = findCard(numId(overId))
      targetList = overCard?.list
      overCardId = overCard?.card.id ?? null
    }
    if (!targetList) return

    // Target list's cards without the dragged one; find where to insert.
    const targetCards = targetList.cards.filter((c) => c.id !== activeId)
    let index = targetCards.length // default: end (dropped on the column body)
    if (overCardId !== null) {
      const i = targetCards.findIndex((c) => c.id === overCardId)
      if (i !== -1) index = i // insert BEFORE the card we dropped on
    }
    // The backend wants "place after this card id" (null = front).
    const afterId = index > 0 ? targetCards[index - 1].id : null

    // Optimistic local move so the UI updates immediately...
    setLists((prev) => {
      const next = prev.map((l) => ({
        ...l,
        cards: l.cards.filter((c) => c.id !== activeId),
      }))
      const moved: Card = { ...source.card, list_id: targetList.id }
      next.find((l) => l.id === targetList.id)!.cards.splice(index, 0, moved)
      return next
    })
    // ...then persist; on success the board query refetches and re-syncs.
    m.moveCard.mutate({ id: activeId, listId: targetList.id, afterId })
  }

  function addList(e: FormEvent) {
    e.preventDefault()
    const t = listTitle.trim()
    if (!t) return
    m.createList.mutate(t)
    setListTitle('')
  }

  return (
    <div className="flex min-h-full flex-col bg-slate-50">
      <AppHeader>
        {board && (
          <>
            <span className="text-slate-400">/ {board.title}</span>
            <div className="relative">
              <button
                onClick={() => setShowMembers((v) => !v)}
                className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
              >
                Members
              </button>
              {showMembers && (
                <MembersPanel
                  boardId={id}
                  ownerId={board.owner_id}
                  onClose={() => setShowMembers(false)}
                />
              )}
            </div>
            <button
              onClick={() => {
                setSummaryOpen(true)
                summarize.mutate()
              }}
              disabled={summarize.isPending}
              className="rounded-md border border-indigo-300 bg-indigo-50 px-2 py-1 text-xs text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
            >
              {summarize.isPending ? 'Summarizing…' : '✨ Summarize'}
            </button>
          </>
        )}
      </AppHeader>

      <main className="flex-1 overflow-x-auto p-4">
        {isLoading && <p className="text-slate-500">Loading…</p>}
        {error && <p className="text-red-600">Couldn't load this board.</p>}

        {board && (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
          >
            <div className="flex items-start gap-3">
              {lists.map((list) => (
                <Column
                  key={list.id}
                  list={list}
                  onAddCard={(title) => m.createCard.mutate({ listId: list.id, title })}
                  onDeleteCard={(cardId) => m.deleteCard.mutate(cardId)}
                  onDeleteList={() => m.deleteList.mutate(list.id)}
                  onOpenCard={(cardId) => setOpenCardId(cardId)}
                />
              ))}

              <form onSubmit={addList} className="w-72 flex-shrink-0">
                <input
                  value={listTitle}
                  onChange={(e) => setListTitle(e.target.value)}
                  placeholder="+ Add a list"
                  className="w-full rounded-lg border border-dashed border-slate-300 bg-white/50 px-3 py-2 text-sm placeholder-slate-400 outline-none focus:border-indigo-400"
                />
              </form>
            </div>

            {/* What you see floating under the cursor while dragging. */}
            <DragOverlay>
              {activeCard ? <CardItem card={activeCard} onDelete={() => {}} /> : null}
            </DragOverlay>
          </DndContext>
        )}
      </main>

      {openCard && (
        <CardModal
          key={openCard.id}
          card={openCard}
          boardId={id}
          onClose={() => setOpenCardId(null)}
        />
      )}

      {summaryOpen && (
        <div
          className="fixed inset-0 z-20 flex items-center justify-center bg-black/30 p-4"
          onClick={() => setSummaryOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-800">Board summary</h3>
              <button
                onClick={() => setSummaryOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            </div>
            {summarize.isPending && (
              <p className="text-slate-500">Generating summary…</p>
            )}
            {summarize.isError && (
              <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
                {summarize.error instanceof Error
                  ? summarize.error.message
                  : 'Failed to summarize.'}
              </p>
            )}
            {summarize.data && (
              <p className="whitespace-pre-wrap text-sm text-slate-700">
                {summarize.data.summary}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
