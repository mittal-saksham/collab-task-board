"""Unit tests for the fractional-ordering helpers (pure math — no database).

These cover the exact rules drag-and-drop relies on: appending to the end, and
dropping between or at the edges of two neighbours. See app/crud/ordering.py and
docs/01-data-model.md for the rationale.
"""

from app.crud.ordering import (
    MIN_GAP,
    POSITION_GAP,
    gap_exhausted,
    position_at_end,
    position_between,
    rebalanced_positions,
)


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


class TestRebalance:
    def test_edges_never_exhausted(self):
        # Inserting at the front/back always has room (the gap just extends).
        assert not gap_exhausted(None, 1e-12)
        assert not gap_exhausted(1e300, None)
        assert not gap_exhausted(None, None)

    def test_wide_gap_not_exhausted(self):
        assert not gap_exhausted(1024.0, 2048.0)

    def test_tiny_gap_is_exhausted(self):
        assert gap_exhausted(100.0, 100.0 + MIN_GAP / 2)
        assert gap_exhausted(100.0, 100.0)  # identical positions (already collided)

    def test_repeated_halving_trips_the_threshold_before_precision_dies(self):
        # Keep halving one gap (the same scenario as the test above, unbounded).
        # gap_exhausted must fire while midpoints are still distinct — i.e. the
        # rebalance triggers BEFORE two cards could ever collide.
        lo, hi = 0.0, POSITION_GAP
        for _ in range(200):
            if gap_exhausted(lo, hi):
                break
            mid = position_between(lo, hi)
            assert lo < mid < hi  # still distinct when we're allowed to insert
            hi = mid
        else:
            raise AssertionError("gap_exhausted never fired")

    def test_rebalanced_positions_are_evenly_spaced_and_ordered(self):
        fresh = rebalanced_positions(5)
        assert fresh == [POSITION_GAP * i for i in range(1, 6)]
        assert fresh == sorted(fresh)

    def test_rebalanced_positions_empty(self):
        assert rebalanced_positions(0) == []
