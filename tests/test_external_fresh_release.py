from __future__ import annotations

import hashlib
import io
import json
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external_fresh_release_registry.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExternalFreshReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registered_hashes(self) -> None:
        self.assertRegex(
            self.registry["release"]["archive_sha256"],
            re.compile(r"^[0-9a-f]{64}$"),
        )
        for panel in self.registry["panels"].values():
            for path_key, hash_key in (
                ("result_file", "result_sha256"),
                ("query_metrics_file", "query_metrics_sha256"),
            ):
                path = ROOT / panel[path_key]
                self.assertEqual(sha256(path), panel[hash_key])
        combined = self.registry["combined_result"]
        self.assertEqual(
            sha256(ROOT / combined["file"]),
            combined["sha256"],
        )
        self.assertEqual(
            sha256(ROOT / self.registry["evidence_archive"]),
            self.registry["evidence_sha256"],
        )

    def test_cross_source_interaction_and_shapes(self) -> None:
        result = json.loads(
            (ROOT / self.registry["combined_result"]["file"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(result["status"], "deltaxrd20_two_source_evaluated")
        self.assertEqual(result["sources"]["rruff"]["contract"]["queries"], 30)
        self.assertEqual(result["sources"]["opxrd"]["contract"]["queries"], 30)
        interaction = result["cross_source_interactions"][
            "rruff_minus_opxrd__crystalshift_adapted_20_minus_window_sqrt_pearson"
        ]["all_present_at_3"]
        self.assertLess(interaction["estimate"], 0)
        self.assertLess(interaction["ci95"][1], 0)

    def test_evidence_has_no_raw_spectra_or_cif(self) -> None:
        archive = ROOT / self.registry["evidence_archive"]
        with zipfile.ZipFile(archive) as handle:
            self.assertIsNone(handle.testzip())
            names = handle.namelist()
            self.assertFalse(any(name.endswith((".xy", ".cif")) for name in names))
            reproduction = json.load(io.BytesIO(handle.read("REPRODUCTION_CHECK.json")))
        self.assertEqual(
            reproduction["status"],
            "deltaxrd20_exact_reproduction",
        )
        self.assertTrue(reproduction["prediction_equal"])
        self.assertTrue(reproduction["sets_equal"])
        self.assertTrue(reproduction["evaluation_equal"])


if __name__ == "__main__":
    unittest.main()
