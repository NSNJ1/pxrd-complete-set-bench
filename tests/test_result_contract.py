from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "evaluation_10000.json"


class FrozenResultTest(unittest.TestCase):
    def test_frozen_result_shape(self) -> None:
        report = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "complete_set_evaluation")
        self.assertEqual(len(report["sources"]), 7)
        self.assertEqual(report["bootstrap"]["repeats"], 10_000)
        self.assertEqual(report["bootstrap"]["seed"], 20261118)

    def test_each_source_has_baseline_and_method(self) -> None:
        report = json.loads(RESULT.read_text(encoding="utf-8"))
        for source in report["sources"].values():
            self.assertIn("baseline", source)
            self.assertIn("method", source)
            self.assertIn("paired_deltas", source)

    def test_reproduction_check(self) -> None:
        check = json.loads(
            (ROOT / "results" / "reproduction_check.json").read_text(encoding="utf-8")
        )
        self.assertEqual(check["status"], "core_reproduction_exact_match")
        self.assertTrue(all(check["checks"].values()))
