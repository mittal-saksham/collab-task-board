"""Unit tests for the fractional-ordering helpers (pure math — no database).

These cover the exact rules drag-and-drop relies on: appending to the end, and
dropping between or at the edges of two neighbours. See app/crud/ordering.py and
docs/01-data-model.md for the rationale.
"""

from app.crud.ordering import POSITION_GAP, position_at_end, position_between


class TestPositionAtEnd:
    def test_empty_list_uses_base_gap(self):
        assert position_at_end(None) == POSITION_GAP

    def test_appends_one_gap_past_the_last(self):
        assert position_at_end(1024.0) == 1024.0 + POSITION_GAP

    def test_strictly_increasing(self):
        # Each append must land after the previous last position.
        last = None
        for _ in range(5):
            nxt = position_at_end(last)
            assert last is None or nxt > last
            last = nxt


class TestPositionBetween:
    def test_empty_list_uses_base_gap(self):
        assert position_between(None, None) == POSITION_GAP

    def test_front_is_half_of_first(self):
        # Dropping before the first item (prev=None) -> next/2: stays > 0 and
        # < next, so it sorts ahead of it.
        assert position_between(None, 100.0) == 50.0

    def test_back_appends_a_gap(self):
        assert position_between(2048.0, None) == 2048.0 + POSITION_GAP

    def test_midpoint_between_two(self):
        assert position_between(100.0, 200.0) == 150.0

    def test_result_is_strictly_between(self):
        prev, nxt = 1024.0, 2048.0
        mid = position_between(prev, nxt)
        assert prev < mid < nxt

    def test_repeated_inserts_into_same_gap_stay_distinct_and_ordered(self):
        # Insert repeatedly toward the front of one gap. Positions must stay
        # distinct and ordered — this is the scenario that eventually exhausts
        # float precision (the rebalance fallback), but holds for many inserts.
        lo, hi = 0.0, 1024.0
        seen = []
        for _ in range(20):
            mid = position_between(lo, hi)
            assert lo < mid < hi
            seen.append(mid)
            hi = mid  # keep inserting ahead of the one we just placed
        assert seen == sorted(seen, reverse=True)  # each new one is smaller
        assert len(set(seen)) == len(seen)  # all distinct
