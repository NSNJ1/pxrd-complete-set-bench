from __future__ import annotations

import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external_stress_registry.json"


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


class ExternalStressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registered_files_and_archives(self) -> None:
        for panel in self.registry["panels"].values():
            for file_key, hash_key in (
                ("result_file", "result_sha256"),
                ("query_metrics_file", "query_metrics_sha256"),
                ("reproduction_file", "reproduction_sha256"),
                ("evidence_archive", "evidence_sha256"),
            ):
                path = ROOT / panel[file_key]
                self.assertTrue(path.is_file(), path)
                self.assertEqual(sha256_file(path), panel[hash_key], path)

    def test_result_contracts(self) -> None:
        realbind = self.registry["panels"]["realbind20_single_phase"]
        xca = self.registry["panels"]["xca20_multiphase"]
        realbind_result = json.loads(
            (ROOT / realbind["result_file"]).read_text(encoding="utf-8")
        )
        xca_result = json.loads((ROOT / xca["result_file"]).read_text(encoding="utf-8"))

        self.assertEqual(realbind_result["contract"]["queries"], 20)
        self.assertEqual(realbind_result["contract"]["candidates"], 20)
        self.assertAlmostEqual(
            realbind_result["methods"]["crystalshift_adapted_20"]["phase_ap_macro"],
            0.8416666666666666,
        )
        self.assertEqual(xca_result["contract"]["queries"], 30)
        self.assertEqual(xca_result["contract"]["candidate_families"], 20)
        self.assertEqual(xca_result["contract"]["candidate_structures"], 31)
        self.assertAlmostEqual(
            xca_result["methods"]["crystalshift_adapted_20"]["phase_ap_macro"],
            0.3002475268109943,
        )
        self.assertAlmostEqual(
            xca_result["methods"]["window_sqrt_pearson"]["all_present_at_3"],
            0.6,
        )

    def test_public_handoffs_contain_no_truth_columns(self) -> None:
        forbidden = (b"label", b"positive", b"target", b"source_name", b"truth")
        for panel in self.registry["panels"].values():
            archive = ROOT / panel["evidence_archive"]
            with zipfile.ZipFile(archive) as handle:
                self.assertIsNone(handle.testzip())
                public_tables = [
                    name
                    for name in handle.namelist()
                    if name.startswith("public/") and name.endswith(".csv")
                ]
                self.assertGreaterEqual(len(public_tables), 2)
                for name in public_tables:
                    content = handle.read(name).lower()
                    self.assertFalse(
                        any(term in content for term in forbidden),
                        name,
                    )

    def test_archived_reproduction_statuses(self) -> None:
        statuses = {}
        for panel in self.registry["panels"].values():
            archive = ROOT / panel["evidence_archive"]
            with zipfile.ZipFile(archive) as handle:
                reproduction = json.load(
                    io.BytesIO(handle.read("REPRODUCTION_CHECK.json"))
                )
            self.assertTrue(reproduction["prediction_equal"])
            self.assertTrue(reproduction["sets_equal"])
            self.assertTrue(reproduction["evaluation_equal"])
            self.assertTrue(reproduction["query_metrics_equal"])
            statuses[panel["reproduction"]] = reproduction["status"]
        self.assertEqual(
            statuses,
            {
                "realbind20_exact_reproduction": ("realbind20_exact_reproduction"),
                "xca20_exact_reproduction": "xca20_exact_reproduction",
            },
        )


if __name__ == "__main__":
    unittest.main()
