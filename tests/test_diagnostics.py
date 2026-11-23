from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.diagnostics import (
    run_diagnostics,
    sample_nested_library,
)

ROOT = Path(__file__).resolve().parent


class DiagnosticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.read_csv(ROOT / "smoke_fixture.csv")

    def test_nested_library_keeps_all_positives(self) -> None:
        group = self.frame.loc[
            self.frame["source"].eq("A") & self.frame["query_id"].eq("q1")
        ]
        subset = sample_nested_library(group, 3, 20261118)
        self.assertIsNotNone(subset)
        self.assertEqual(
            set(subset.loc[subset["present"].eq(1), "phase_id"]),
            {"P1", "P2"},
        )
        repeated = sample_nested_library(group, 3, 20261118)
        self.assertEqual(
            list(subset["phase_id"]),
            list(repeated["phase_id"]),
        )

    def test_nested_library_rejects_size_below_positive_count(self) -> None:
        group = self.frame.loc[
            self.frame["source"].eq("B") & self.frame["query_id"].eq("r2")
        ]
        self.assertIsNone(sample_nested_library(group, 2, 20261118))

    def test_diagnostics_sections_reconcile(self) -> None:
        report, failures, confidence = run_diagnostics(
            self.frame,
            ("baseline_score", "method_score"),
            sizes=(2, 3, None),
            budgets=(1, 2, 3),
            review_budget=2,
            coverages=(0.5, 1.0),
            bootstrap_repeats=20,
            sampling_replicates=2,
            seed=20261118,
        )
        self.assertEqual(report["status"], "complete_set_diagnostics")
        self.assertFalse(report["contract"]["confidence_is_probability"])
        for source in report["failure_taxonomy"].values():
            for method in source.values():
                counts = [row["count"] for row in method["categories"].values()]
                self.assertEqual(sum(counts), method["queries"])
        source_a = report["risk_coverage"]["sources"]["A"]["method_score"]
        self.assertEqual(
            source_a["normalized_boundary_margin"]["1.0"]["queries"],
            2,
        )
        self.assertEqual(len(failures), 8)
        self.assertEqual(len(confidence), 8)


if __name__ == "__main__":
    unittest.main()
