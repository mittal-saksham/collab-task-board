import { useEffect, useRef } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { Card } from '../types'
import { CardBadges } from './CardBadges'

// A card that can be dragged AND clicked to open its detail modal. useSortable
// gives us the refs/handlers and the live transform while dragging; we spread
// them onto the card div. dnd-kit ids must be unique across the whole board, so
// we prefix: `card-<id>`.
export function SortableCard({
  card,
  onDelete,
  onOpen,
}: {
  card: Card
  onDelete: () => void
  onOpen: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `card-${card.id}` })

  // Distinguish a real drag from a plain click. The problem: after you drag and
  // drop a card, the browser may still fire a `click` — which would wrongly open
  // the modal. dnd-kit flips `isDragging` true at some point during ANY real
  // drag, but it's already back to false by the time the click fires. So we LATCH
  // it into a ref while it's true; the click handler reads that latch to know a
  // drag just happened. (A distance check would fail the "pick up and drop in
  // place" case; latching the actual drag state is exact.)
  const dragged = useRef(false)
  useEffect(() => {
    if (isDragging) dragged.current = true
  }, [isDragging])

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1, // ghost the original while it's being dragged
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      // Capture phase runs BEFORE dnd-kit's (bubble-phase) onPointerDown, so this
      // doesn't collide with it. We reset the latch at the start of each gesture.
      onPointerDownCapture={() => {
        dragged.current = false
      }}
      onClick={() => {
        if (dragged.current) {
          dragged.current = false
          return // this "click" is the tail end of a drag — ignore it
        }
        onOpen()
      }}
      className="group cursor-grab rounded-md bg-white p-2 shadow-sm ring-1 ring-slate-200 transition hover:ring-indigo-300 active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-800">{card.title}</p>
        <button
          // stopPropagation on pointerdown so clicking × doesn't start a drag,
          // and on click so deleting doesn't ALSO bubble up and open the modal.
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          title="Delete card"
          className="text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-red-500"
        >
          ×
        </button>
      </div>
      {card.description && (
        <p className="mt-1 text-xs text-slate-500">{card.description}</p>
      )}
      <CardBadges card={card} />
    </div>
  )
}
