import type { Card } from '../types'
import { CardBadges } from './CardBadges'

// A single task card. `group` + `opacity-0 group-hover:opacity-100` is a Tailwind
// pattern: the × button is hidden until you hover the card. This version is used
// for the floating DragOverlay; the on-board card is SortableCard.
export function CardItem({ card, onDelete }: { card: Card; onDelete: () => void }) {
  return (
    <div className="group rounded-md bg-white p-2 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-800">{card.title}</p>
        <button
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
      <CardBadges card={card} />
    </div>
  )
}
