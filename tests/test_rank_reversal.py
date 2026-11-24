from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from pxrd_complete_set_bench.rank_reversal import (
    _average_ranks,
    _pairwise_reversal_fraction,
    rank_reversal_report,
)


class RankReversalTest(unittest.TestCase):
    def test_average_ranks_share_tied_positions(self) -> None:
        ranks = _average_ranks(
            np.asarray([0.9, 0.8, 0.8, 0.1]),
            higher_is_better=True,
        )
        np.testing.assert_allclose(ranks, [1.0, 2.5, 2.5, 4.0])

    def test_pairwise_reversal_counts_only_comparable_pairs(self) -> None:
        fraction, comparable = _pairwise_reversal_fraction(
            np.asarray([0.9, 0.8, 0.8]),
            np.asarray([0.1, 0.8, 0.7]),
            True,
            True,
        )
        self.assertEqual(comparable, 2)
        self.assertEqual(fraction, 1.0)

    def test_tiny_panel_report_has_headline(self) -> None:
        frame = pd.DataFrame(
            {
                "query_id": ["q1"] * 3 + ["q2"] * 3,
                "phase_id": ["A", "B", "C"] * 2,
                "present": [1, 1, 0, 1, 0, 0],
                "m1": [0.9, 0.8, 0.1, 0.7, 0.6, 0.1],
                "m2": [0.8, 0.9, 0.1, 0.8, 0.2, 0.1],
                "m3": [0.2, 0.1, 0.9, 0.3, 0.2, 0.1],
            }
        )
        report = rank_reversal_report(
            frame,
            ("m1", "m2", "m3"),
            budgets=(1, 2, 3),
            repeats=20,
            seed=7,
        )
        self.assertIn("headline", report)
        self.assertEqual(report["contract"]["queries"], 2)

    def test_required_budgets_are_explicit(self) -> None:
        frame = pd.DataFrame(
            {
                "query_id": ["q1"] * 2,
                "phase_id": ["A", "B"],
                "present": [1, 0],
                "m1": [0.9, 0.1],
            }
        )
        with self.assertRaisesRegex(ValueError, "budgets 2 and 3"):
            rank_reversal_report(frame, ("m1",), budgets=(1, 3), repeats=5)


if __name__ == "__main__":
    unittest.main()
