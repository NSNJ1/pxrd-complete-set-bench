from __future__ import annotations

import hashlib
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

    def test_external_method_evidence(self) -> None:
        evidence = ROOT / "evidence" / "external-methods"
        for name in (
            "CRYSTALSHIFT_INDEPENDENT_RUN_20261123_PUBLIC_SANITIZED.zip",
            "XRD_AUTOANALYZER_INDEPENDENT_RUN_20261123_PUBLIC_SANITIZED.zip",
            "XMATCHER_AUTOMIX_LOCAL_RUN_20261123_PUBLIC_SANITIZED.zip",
            "XDECOMPOSER_LOCAL_RUN_20261123_PUBLIC_SANITIZED.zip",
            "MINGHAO_CRYSTALSHIFT_CONFIRMATION.json",
            "MINGHAO_XRD_CONFIRMATION.json",
        ):
            self.assertTrue((evidence / name).is_file(), name)
        expected_hashes = {
            "CRYSTALSHIFT_INDEPENDENT_RUN_20261123_PUBLIC_SANITIZED.zip": (
                "31dfa3143e22f96fa797ad209d34cd0994a81f725a18422d714c9a4d27fd4c47"
            ),
            "XRD_AUTOANALYZER_INDEPENDENT_RUN_20261123_PUBLIC_SANITIZED.zip": (
                "6aa6ea4322af8f42ea43d4a29743eb684441adfa00a5b577005093bb8524a9ee"
            ),
            "XMATCHER_AUTOMIX_LOCAL_RUN_20261123_PUBLIC_SANITIZED.zip": (
                "e6e3f3792d630d3152d2a9167e5c36e0bea060cd7ee4f7bd45d8f5ba7fadfd5b"
            ),
            "XDECOMPOSER_LOCAL_RUN_20261123_PUBLIC_SANITIZED.zip": (
                "c84b3ee8d8eb1d0ea4c6c638548d7001315215db5a3d0256131d54e101a471fa"
            ),
        }
        for name, expected in expected_hashes.items():
            actual = hashlib.sha256((evidence / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected)

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
