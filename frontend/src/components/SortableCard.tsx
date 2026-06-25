import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { Card } from '../types'

// A card that can be dragged. useSortable gives us the refs/handlers and the
// live transform while dragging; we spread them onto the card div.
// dnd-kit ids must be unique across the whole board, so we prefix: `card-<id>`.
export function SortableCard({ card, onDelete }: { card: Card; onDelete: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `card-${card.id}` })

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
      className="group cursor-grab rounded-md bg-white p-2 shadow-sm ring-1 ring-slate-200 active:cursor-grabbing"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-800">{card.title}</p>
        <button
          // stopPropagation on pointerdown so clicking × doesn't start a drag
          onPointerDown={(e) => e.stopPropagation()}
          onClick={onDelete}
          title="Delete card"
          className="text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-red-500"
        >
          ×
        </button>
      </div>
      {card.description && (
        <p className="mt-1 text-xs text-slate-500">{card.description}</p>
      )}
    </div>
  )
}
