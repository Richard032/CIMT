"""Verify shared budget admission and settlement with counted request input."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from budget import Budget, PRICING
from errors import LimitReached


class BudgetReservationTests(unittest.TestCase):
    def test_counted_input_reservation_allows_output_to_overrun(self):
        budget = Budget(next(iter(PRICING)), '0.01', 'USD')

        reservation = budget.reserve(10_000)

        self.assertEqual(reservation.input_tokens, 10_000)
        self.assertEqual(reservation.estimated, Decimal('0.0075'))
        budget.finish(dict(input_tokens=10_000, output_tokens=1000), reservation=reservation)
        self.assertEqual(budget.accounted, Decimal('0.012'))
        self.assertEqual(Decimal(budget.snapshot()['budgetOverrun']), Decimal('0.002'))
        with self.assertRaisesRegex(LimitReached, 'counted request input'):
            budget.reserve(50)

    def test_concurrent_estimates_share_the_remaining_budget(self):
        budget = Budget(next(iter(PRICING)), '0.012', 'USD')

        def try_reserve(input_tokens):
            try:
                return budget.reserve(input_tokens)
            except LimitReached:
                return None

        with ThreadPoolExecutor(max_workers=2) as workers:
            attempts = list(workers.map(try_reserve, [9_500, 10_000]))

        reservations = [reservation for reservation in attempts if reservation is not None]
        self.assertEqual(len(reservations), 1)
        self.assertEqual(budget.pending, reservations[0].estimated)
        self.assertEqual(budget.requests, 1)

    def test_inflight_estimate_restores_at_counted_input_plus_full_output_when_usage_unknown(self):
        budget = Budget(next(iter(PRICING)), '1', 'USD')
        request_one = budget.reserve(200)
        request_two = budget.reserve(300)
        budget.release_unsent(request_two)
        snapshot = budget.snapshot()
        self.assertEqual(Decimal(snapshot['pendingEstimatedCost']), request_one.estimated)
        self.assertEqual(Decimal(snapshot['pendingUpperCost']), request_one.maximum)

        restored = Budget(budget.model, '1', 'USD')
        restored.restore(snapshot)
        self.assertEqual(restored.uncertain, request_one.maximum)
        self.assertEqual(restored.requests, 1)

    def test_reservation_can_fit_when_maximum_output_would_not(self):
        budget = Budget(next(iter(PRICING)), '0.001', 'USD')
        reservation = budget.reserve(1000)
        self.assertEqual(reservation.estimated, Decimal('0.00075'))
        self.assertGreater(reservation.maximum, budget.limit)

    def test_legacy_pending_snapshot_still_restores(self):
        budget = Budget(next(iter(PRICING)), '1', 'USD')
        budget.reserve()
        snapshot = budget.snapshot()
        del snapshot['pendingEstimatedCost']
        restored = Budget(budget.model, '1', 'USD')
        restored.restore(snapshot)
        self.assertEqual(restored.uncertain, budget.bound)
