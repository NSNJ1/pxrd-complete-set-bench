"""Deterministic tests for the evaluator."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.evaluate import (
    evaluate,
    rank_queries,
    screen_diagnostics,
    validate,
)

ROOT = Path(__file__).resolve().parent


class CompleteSetEvaluatorTest(unittest.TestCase):
    def test_fixture_metrics_and_strata(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        report = evaluate(
            frame,
            "baseline_score",
            "method_score",
            (1, 2, 3),
            100,
            20261118,
        )
        self.assertEqual(set(report["sources"]), {"A", "B"})
        self.assertAlmostEqual(
            report["sources"]["A"]["baseline"]["phase_ap_micro"],
            0.9166666666666666,
        )
        self.assertAlmostEqual(
            report["sources"]["A"]["method"]["phase_ap_micro"],
            1.0,
        )
        self.assertAlmostEqual(
            report["sources"]["A"]["baseline"]["all_present_at_2"],
            1.0,
        )
        self.assertAlmostEqual(
            report["sources"]["B"]["baseline"]["all_present_at_2"],
            0.0,
        )
        self.assertAlmostEqual(
            report["sources"]["B"]["method"]["all_present_at_2"],
            0.5,
        )
        self.assertAlmostEqual(
            report["sources"]["B"]["method"]["all_present_at_2_set_macro"],
            0.5,
        )
        self.assertAlmostEqual(
            report["sources"]["B"]["method"]["all_present_at_2_cardinality_balanced"],
            0.5,
        )
        self.assertEqual(
            set(report["sources"]["B"]["baseline"]["cardinality_results"]),
            {"2", "3"},
        )
        self.assertEqual(
            report["sources"]["B"]["baseline"]["cardinality_results"]["3"]["queries"],
            1,
        )
        self.assertIn(
            "all_present_at_3",
            report["sources"]["B"]["cardinality_paired_deltas"]["3"],
        )
        screen = report["sources"]["B"]["screen_diagnostics"]["2"]
        self.assertEqual(screen["queries"], 2)
        self.assertAlmostEqual(
            screen["true_phase_recall"]["baseline"],
            7 / 12,
        )
        self.assertEqual(
            screen["same_baseline_screen_phase_ap_macro"]["queries"],
            1,
        )

    def test_duplicate_candidate_rejected(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(duplicated, "baseline_score", "method_score")

    def test_missing_primary_is_supported(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        frame["primary"] = pd.NA
        report = evaluate(
            frame,
            "baseline_score",
            "method_score",
            (1, 2, 3),
            20,
            20261118,
        )
        self.assertIsNone(report["sources"]["A"]["method"]["dominant_top1"])
        self.assertIsNone(
            report["sources"]["A"]["method"]["cardinality_results"]["2"][
                "dominant_top1"
            ]
        )

    def test_inconsistent_query_cluster_rejected(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        frame.loc[1, "cluster_id"] = "wrong-cluster"
        with self.assertRaisesRegex(ValueError, "exactly one cluster"):
            validate(frame, "baseline_score", "method_score")

    def test_primary_phase_must_be_present(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        absent_index = frame.index[frame["present"].eq(0)][0]
        frame.loc[absent_index, "primary"] = 1
        with self.assertRaisesRegex(ValueError, "must also be present"):
            validate(frame, "baseline_score", "method_score")

    def test_bootstrap_repeats_must_be_positive(self) -> None:
        frame = pd.read_csv(ROOT / "smoke_fixture.csv")
        with self.assertRaisesRegex(ValueError, "bootstrap repeats"):
            evaluate(
                frame,
                "baseline_score",
                "method_score",
                (1, 2, 3),
                0,
                20261118,
            )

    def test_tied_scores_use_phase_id_regardless_of_input_order(self) -> None:
        rows = [
            {
                "source": "s",
                "query_id": "q",
                "cluster_id": "c",
                "phase_id": phase_id,
                "present": int(phase_id in {"A", "D"}),
                "baseline_score": 1.0,
                "method_score": 1.0,
            }
            for phase_id in "ABCD"
        ]
        expected = rank_queries(pd.DataFrame(rows), "method_score", (1, 2))
        shuffled = rank_queries(
            pd.DataFrame([rows[3], rows[1], rows[2], rows[0]]),
            "method_score",
            (1, 2),
        )
        columns = ["top1_present", "all_present_at_1", "all_present_at_2"]
        self.assertEqual(
            expected[columns].to_dict("records"), shuffled[columns].to_dict("records")
        )
        self.assertEqual(expected.loc[0, "all_present_at_1"], 0.0)
        self.assertEqual(expected.loc[0, "all_present_at_2"], 0.0)

        expected_screen = screen_diagnostics(
            pd.DataFrame(rows),
            "baseline_score",
            "method_score",
            (2,),
            20,
            20261118,
        )
        shuffled_screen = screen_diagnostics(
            pd.DataFrame([rows[3], rows[1], rows[2], rows[0]]),
            "baseline_score",
            "method_score",
            (2,),
            20,
            20261118,
        )
        self.assertEqual(expected_screen, shuffled_screen)


if __name__ == "__main__":
    unittest.main()
