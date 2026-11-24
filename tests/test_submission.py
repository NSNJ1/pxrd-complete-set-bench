from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from pxrd_complete_set_bench.cli import main
from pxrd_complete_set_bench.submission import (
    average_precision_with_missing,
    score_submission,
)


class SubmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.truth = pd.DataFrame(
            {
                "source": ["A"] * 4,
                "query_id": ["q1"] * 4,
                "cluster_id": ["c1"] * 4,
                "phase_id": ["P1", "P2", "P3", "P4"],
                "present": [1, 1, 0, 0],
            }
        )

    def test_complete_submission_has_full_coverage(self) -> None:
        predictions = pd.DataFrame(
            {
                "method_id": ["m"] * 4,
                "source": ["A"] * 4,
                "query_id": ["q1"] * 4,
                "phase_id": ["P1", "P2", "P3", "P4"],
                "score": [1.0, 0.9, 0.8, 0.7],
            }
        )
        report = score_submission(
            self.truth,
            predictions,
            budgets=(1, 2, 3),
            repeats=20,
        )
        source = report["methods"]["m"]["sources"]["A"]
        self.assertEqual(source["metrics"]["candidate_coverage"], 1.0)
        self.assertEqual(source["metrics"]["all_present_at_2"], 1.0)

    def test_missing_true_phase_prevents_complete_set_success(self) -> None:
        predictions = pd.DataFrame(
            {
                "method_id": ["m"] * 3,
                "source": ["A"] * 3,
                "query_id": ["q1"] * 3,
                "phase_id": ["P1", "P3", "P4"],
                "score": [1.0, 0.8, 0.7],
            }
        )
        report = score_submission(
            self.truth,
            predictions,
            budgets=(1, 2, 3),
            repeats=20,
        )
        source = report["methods"]["m"]["sources"]["A"]
        self.assertLess(source["metrics"]["candidate_coverage"], 1.0)
        self.assertEqual(source["metrics"]["positive_coverage"], 0.5)
        self.assertEqual(source["metrics"]["all_present_at_3"], 0.0)

    def test_ap_counts_missing_positive_in_recall_denominator(self) -> None:
        value = average_precision_with_missing(
            np.asarray([1, 0]),
            np.asarray([1.0, 0.0]),
            pd.Series(["P1", "P3"]),
            total_positive_count=2,
        )
        self.assertAlmostEqual(value, 0.5)

    def test_unknown_candidate_is_rejected(self) -> None:
        predictions = pd.DataFrame(
            {
                "method_id": ["m"],
                "source": ["A"],
                "query_id": ["q1"],
                "phase_id": ["unknown"],
                "score": [1.0],
            }
        )
        with self.assertRaisesRegex(ValueError, "unknown candidate"):
            score_submission(
                self.truth,
                predictions,
                budgets=(1, 2),
                repeats=10,
            )

    def test_uncovered_query_stays_in_primary_denominator(self) -> None:
        truth = pd.concat(
            [
                self.truth,
                self.truth.assign(query_id="q2", cluster_id="c2"),
            ],
            ignore_index=True,
        )
        predictions = pd.DataFrame(
            {
                "method_id": ["m"] * 4,
                "source": ["A"] * 4,
                "query_id": ["q1"] * 4,
                "phase_id": ["P1", "P2", "P3", "P4"],
                "score": [1.0, 0.9, 0.8, 0.7],
            }
        )
        report = score_submission(
            truth,
            predictions,
            budgets=(1, 2),
            repeats=20,
        )
        method = report["methods"]["m"]
        self.assertEqual(method["query_coverage"], 0.5)
        self.assertEqual(method["sources"]["A"]["metrics"]["all_present_at_2"], 0.5)
        self.assertEqual(
            method["sources"]["A"]["metrics"]["covered_query_all_present_at_2"],
            1.0,
        )

    def test_cli_writes_submission_report(self) -> None:
        predictions = pd.DataFrame(
            {
                "method_id": ["m"] * 3,
                "source": ["A"] * 3,
                "query_id": ["q1"] * 3,
                "phase_id": ["P1", "P2", "P3"],
                "score": [1.0, 0.9, 0.8],
            }
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            truth_path = root / "truth.csv"
            predictions_path = root / "predictions.csv"
            output_path = root / "result.json"
            self.truth.to_csv(truth_path, index=False)
            predictions.to_csv(predictions_path, index=False)
            code = main(
                [
                    "score-submission",
                    str(truth_path),
                    str(predictions_path),
                    "--budgets",
                    "1,2,3",
                    "--bootstrap-repeats",
                    "10",
                    "--output-json",
                    str(output_path),
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(output_path.is_file())


if __name__ == "__main__":
    unittest.main()
