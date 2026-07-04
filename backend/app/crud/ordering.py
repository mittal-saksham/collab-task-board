"""Fractional ordering helpers (shared by lists and cards).

Each orderable item carries a float `position`. To drop an item between two
neighbours we use the MIDPOINT of their positions, so a move is normally a
single-row UPDATE. The rare exception: when the gap between the neighbours is
exhausted (`gap_exhausted`), the CRUD layer renumbers that one list's siblings
with `rebalanced_positions` before placing the item. See docs/01-data-model.md.

These functions are PURE (just math on numbers); the CRUD layer is responsible
for fetching the neighbour positions to pass in.
"""

# Spacing used when appending to the end of a list. A wide gap leaves lots of
# room to insert between items before precision becomes a concern.
POSITION_GAP = 1024.0

# When the gap between two neighbours shrinks below this, midpoints are about to
# stop producing distinct values (float64 runs out of bits after ~50 halvings of
# the base gap), so the CRUD layer renumbers the siblings first.
MIN_GAP = 1e-6


def gap_exhausted(prev_position: float | None, next_position: float | None) -> bool:
    """True when there is no usable room left between two neighbours."""
    if prev_position is None or next_position is None:
        return False  # inserting at an edge always has room
    return (next_position - prev_position) <= MIN_GAP


def rebalanced_positions(count: int) -> list[float]:
    """Fresh, evenly-spaced positions for `count` items (the rebalance step).

    Keeps the items' relative order; the caller assigns these in that order.
    """
    return [POSITION_GAP * (i + 1) for i in range(count)]


def position_at_end(last_position: float | None) -> float:
    """Position for a new item appended after the current last one.

    `last_position` is the max position among existing siblings, or None if the
    list is empty.
    """
    if last_position is None:
        return POSITION_GAP
    return last_position + POSITION_GAP


def position_between(
    prev_position: float | None, next_position: float | None
) -> float:
    """Position to drop an item between two neighbours.

    Either side may be None when dropping at an edge:
      - both None  -> empty list, use the base gap
      - prev None  -> dropping at the FRONT (before the first item)
      - next None  -> dropping at the BACK (after the last item)
      - otherwise  -> the midpoint of the two
    """
    if prev_position is None and next_position is None:
        return POSITION_GAP
    if prev_position is None:
        return next_position / 2
    if next_position is None:
        return prev_position + POSITION_GAP
    return (prev_position + next_position) / 2
