"""Fractional ordering helpers (shared by lists and cards).

Each orderable item carries a float `position`. To drop an item between two
neighbours we use the MIDPOINT of their positions, so a move is a single-row
UPDATE — we never renumber siblings. See docs/01-data-model.md for the full
rationale and the rebalance fallback.

These functions are PURE (just math on numbers); the CRUD layer is responsible
for fetching the neighbour positions to pass in.
"""

# Spacing used when appending to the end of a list. A wide gap leaves lots of
# room to insert between items before precision becomes a concern.
POSITION_GAP = 1024.0


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
