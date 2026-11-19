from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.evaluate import validate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "query_phase_scores.csv"


class PublicDataContractTest(unittest.TestCase):
    def test_frozen_counts_and_hash(self) -> None:
        self.assertEqual(
            hashlib.sha256(DATA.read_bytes()).hexdigest(),
            "70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b",
        )
        frame = pd.read_csv(DATA)
        self.assertEqual(len(frame), 57_991)
        self.assertEqual(frame["source"].nunique(), 7)
        self.assertEqual(
            frame.groupby(["source", "query_id"]).ngroups,
            1_921,
        )
        validate(frame, "baseline_score", "method_score")

    def test_required_sources(self) -> None:
        frame = pd.read_csv(DATA, usecols=["source"])
        self.assertEqual(
            set(frame["source"]),
            {
                "ariadnex_controlled",
                "galaxi_pristine",
                "galaxi_validation",
                "precursor_genome",
                "rare_earth_mof",
                "tasno",
                "xca_nicoal",
            },
        )
