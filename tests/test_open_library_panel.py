from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PANEL = REPO / "evidence" / "open-library-precursor-genome-v0.8"


class OpenLibraryPanelTests(unittest.TestCase):
    def test_source_overlap_is_explicit(self) -> None:
        overlap = json.loads(
            (PANEL / "PRIOR_PROJECT_OVERLAP_20261127.json").read_text(
                encoding="utf-8"
            )
        )
        prior_ids = {
            line.strip()
            for line in (PANEL / "PRIOR_PROJECT_QUERY_IDS.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        }
        query_rows = (
            PANEL / "dataset_v7" / "public" / "queries.csv"
        ).read_text(encoding="utf-8").splitlines()[1:]
        current_ids = {row.split(",", 1)[0] for row in query_rows}

        self.assertEqual(len(prior_ids), 416)
        self.assertEqual(len(current_ids), 102)
        self.assertEqual(len(prior_ids & current_ids), 77)
        self.assertEqual(len(current_ids - prior_ids), 25)
        self.assertEqual(overlap["overlap"]["exact_query_id_overlap"], 77)

    def test_case_and_release_counts(self) -> None:
        case_manifest = json.loads(
            (PANEL / "cases_v8" / "manifest.json").read_text(encoding="utf-8")
        )
        release_manifest = json.loads(
            (PANEL / "RELEASE_FILE_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(case_manifest["queries"], 102)
        self.assertEqual(case_manifest["cases"], 418)
        self.assertEqual(case_manifest["case_phase_truth_rows"], 8044)
        self.assertEqual(release_manifest["file_count"], 444)

    def test_primary_endpoint_values(self) -> None:
        summary = json.loads(
            (PANEL / "scores_v8" / "summary.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "profile_baseline": (0.7082417078981125, 0.5071009712296134),
            "crystalshift": (0.8043567894447499, 0.5024280740333517),
            "xdecomposer": (0.5632673630199744, 0.5061389041597947),
        }
        for method, (actual, fixed) in expected.items():
            card = summary["methods"][method]
            self.assertAlmostEqual(
                card["unknown_endpoint"]["actual"]["all"]["auroc"],
                actual,
            )
            self.assertAlmostEqual(
                card["unknown_endpoint"]["fixed_full_residual"]["all"]["auroc"],
                fixed,
            )


if __name__ == "__main__":
    unittest.main()
