from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicSurfaceTest(unittest.TestCase):
    def test_release_files_exist(self) -> None:
        for name in (
            "README.md",
            "LICENSE",
            "LICENSE-DATA",
            "NOTICE",
            "CITATION.cff",
            "pyproject.toml",
        ):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_external_control_summary(self) -> None:
        summary = json.loads(
            (ROOT / "results" / "external_controls" / "summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(summary["controls"]),
            {"mangolini_ternary", "usgs_high_cardinality"},
        )
        self.assertEqual(
            summary["controls"]["mangolini_ternary"]["queries"],
            28,
        )
        self.assertEqual(
            summary["controls"]["usgs_high_cardinality"]["queries"],
            65,
        )
