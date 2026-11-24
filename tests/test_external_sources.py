from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external_source_registry.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExternalSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_result_hashes_and_shapes(self) -> None:
        expected = {
            "opxrd_empa_multiphase": (200, 4),
            "realbind_mini_single_phase": (104, 104),
        }
        for name, (queries, candidates) in expected.items():
            source = self.registry["sources"][name]
            result_path = ROOT / source["result_file"]
            self.assertEqual(sha256(result_path), source["result_sha256"])
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["contract"]["queries"], queries)
            self.assertEqual(result["contract"]["candidates"], candidates)

    def test_evidence_archives(self) -> None:
        for source in self.registry["sources"].values():
            archive = ROOT / source["evidence_archive"]
            self.assertTrue(archive.is_file(), archive)
            self.assertEqual(
                sha256(archive),
                source["evidence_sha256"],
            )

    def test_reproduction_statuses(self) -> None:
        statuses = {
            source["reproduction"] for source in self.registry["sources"].values()
        }
        self.assertEqual(
            statuses,
            {
                "opxrd_empa_reproduction_exact_match",
                "realbind_mini_reproduction_exact_match",
            },
        )

    def test_overlap_and_statistical_audits(self) -> None:
        overlap = json.loads(
            (ROOT / "results" / "source_overlap_audit.json").read_text(encoding="utf-8")
        )
        null_audit = json.loads(
            (ROOT / "results" / "null_and_power_audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(overlap["status"], "source_overlap_audit")
        self.assertEqual(null_audit["status"], "null_and_power_audit")
        self.assertEqual(len(null_audit["sources"]), 7)
        self.assertEqual(
            sha256(ROOT / "results" / "source_overlap_audit.json"),
            "c75361582ed5f28609313a59d9c4c708eb69fe9da2be65583d72a8322e26395e",
        )
        self.assertEqual(
            sha256(ROOT / "results" / "null_and_power_audit.json"),
            sha256(ROOT / "results" / "null_and_power_audit_reproduction.json"),
        )

    def test_rank_reversal_audit(self) -> None:
        result_path = ROOT / "results" / "rank_reversal_audit.json"
        self.assertEqual(
            sha256(result_path),
            "6c94c76f009435ed0c991909b5774300a6a82a37d6578bcce9a0d3d57e437595",
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "endpoint_rank_reversal_audit")
        self.assertEqual(result["contract"]["queries"], 25)
        self.assertEqual(result["contract"]["methods"], 8)
        self.assertEqual(
            result["headline"]["observed_pairwise_reversal_fraction"],
            0.12,
        )
        self.assertEqual(
            sha256(result_path),
            sha256(ROOT / "results" / "rank_reversal_audit_reproduction.json"),
        )


if __name__ == "__main__":
    unittest.main()
