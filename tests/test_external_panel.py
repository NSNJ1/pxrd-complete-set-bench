from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import numpy as np

from pxrd_complete_set_bench.external_panel import (
    _average_precision,
    evaluate_external_panel,
    load_predictions,
    load_registry,
    load_truth,
)

ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "data" / "query_phase_scores.csv"
PREDICTIONS = ROOT / "data" / "ariadnex_external_method_predictions.csv"
REGISTRY = ROOT / "data" / "external_method_registry.json"


class ExternalPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_registry(REGISTRY)
        cls.method_ids = tuple(method["id"] for method in cls.registry["methods"])
        cls.truth = load_truth(TRUTH)
        cls.predictions = load_predictions(PREDICTIONS, cls.method_ids)

    def test_prediction_grid_and_hash(self) -> None:
        self.assertEqual(len(self.predictions), 600)
        self.assertEqual(set(self.predictions["method_id"]), set(self.method_ids))
        self.assertEqual(
            hashlib.sha256(PREDICTIONS.read_bytes()).hexdigest(),
            "94826151d17b2ce3776329025e363e1734a142c0442269aaf75d50e4ff0162e1",
        )

    def test_known_metrics_and_tie_bounds(self) -> None:
        report = evaluate_external_panel(
            self.truth,
            self.predictions,
            self.registry,
            repeats=20,
            seed=20261123,
        )
        expected = {
            "deterministic_random": (0.5453911450, 0.16, 0.32),
            "global_sqrt_pearson": (0.9462129471, 0.60, 0.88),
            "window_sqrt_pearson": (0.9357896181, 0.60, 0.92),
            "anchored_set_strict": (0.9618912539, 0.60, 0.92),
            "crystalshift": (0.9420182358, 0.52, 0.76),
            "xrd_autoanalyzer": (0.9319053185, 0.60, 0.80),
        }
        for method, values in expected.items():
            metrics = report["methods"][method]["metrics"]
            self.assertAlmostEqual(metrics["phase_ap_micro"], values[0])
            self.assertAlmostEqual(metrics["all_present_at_2"], values[1])
            self.assertAlmostEqual(metrics["all_present_at_3"], values[2])

        xrd_bounds = report["methods"]["xrd_autoanalyzer"]["tie_order_bounds"][
            "all_present"
        ]
        self.assertEqual(xrd_bounds["3"], {"min": 0.72, "max": 0.88})

    def test_ap_uses_score_blocks_for_ties(self) -> None:
        labels = np.array([1, 0, 1, 0])
        scores = np.array([1.0, 1.0, 0.0, 0.0])
        self.assertAlmostEqual(_average_precision(labels, scores), 0.5)

    def test_registry_lists_two_external_methods(self) -> None:
        external = {
            method["id"]
            for method in self.registry["methods"]
            if method.get("execution") == "independent external execution"
        }
        self.assertEqual(external, {"crystalshift", "xrd_autoanalyzer"})


if __name__ == "__main__":
    unittest.main()
