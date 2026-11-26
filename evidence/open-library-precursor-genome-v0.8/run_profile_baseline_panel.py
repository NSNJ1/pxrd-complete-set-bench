#!/usr/bin/env python3
"""Run an independently scored reference-profile correlation baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

GRID = np.arange(10.0, 100.0001, 0.02)
SHIFTS = np.arange(-0.30, 0.3001, 0.02)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_profile(path: Path) -> np.ndarray:
    values = pd.read_csv(path)
    profile = np.interp(
        GRID,
        values["two_theta"].to_numpy(dtype=float),
        values["intensity"].to_numpy(dtype=float),
        left=0.0,
        right=0.0,
    )
    profile = np.clip(profile, 0.0, None)
    profile -= profile.mean()
    norm = np.linalg.norm(profile)
    if norm <= 0:
        raise ValueError(f"empty profile: {path}")
    return profile / norm


def load_measurement(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    profile = np.interp(
        GRID,
        values[:, 0].astype(float),
        np.clip(values[:, 1].astype(float), 0.0, None),
        left=0.0,
        right=0.0,
    )
    profile -= profile.mean()
    norm = np.linalg.norm(profile)
    if norm <= 0:
        raise ValueError(f"empty measurement: {path}")
    return profile / norm


def shifted_score(
    measurement: np.ndarray,
    reference: np.ndarray,
) -> float:
    maximum = 0.0
    for shift in SHIFTS:
        shifted = np.interp(
            GRID + shift,
            GRID,
            reference,
            left=0.0,
            right=0.0,
        )
        centered = shifted - shifted.mean()
        norm = np.linalg.norm(centered)
        if norm > 0:
            maximum = max(
                maximum,
                float(np.clip(np.dot(measurement, centered / norm), 0.0, 1.0)),
            )
    return maximum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    cases_manifest = json.loads(
        (args.cases / "manifest.json").read_text(encoding="utf-8")
    )
    candidates = pd.read_csv(
        args.dataset / "public" / "candidates.csv",
        dtype=str,
    ).sort_values("candidate_id")
    queries = pd.read_csv(
        args.dataset / "public" / "queries.csv",
        dtype={"query_id": str},
    )
    cases = pd.read_csv(args.cases / "cases.csv", dtype=str).fillna("")
    truth = pd.read_csv(
        args.cases / "case_phase_truth.csv",
        dtype={"case_id": str, "phase_id": str, "present": int},
    )
    candidate_ids = candidates["candidate_id"].tolist()
    references = {
        row.candidate_id: load_profile(
            args.dataset / row.reference_profile_file
        )
        for row in candidates.itertuples(index=False)
    }

    query_scores = {}
    for row in queries.itertuples(index=False):
        measurement = load_measurement(args.dataset / row.spectrum_file)
        query_scores[str(row.query_id)] = {
            candidate_id: shifted_score(
                measurement,
                references[candidate_id],
            )
            for candidate_id in candidate_ids
        }

    rows_candidate = []
    rows_candidate_fixed = []
    rows_case = []
    rows_case_fixed = []
    for case in cases.itertuples(index=False):
        available = sorted(
            truth.loc[
                truth["case_id"].eq(case.case_id),
                "phase_id",
            ].tolist()
        )
        if len(available) != int(case.candidate_count):
            raise ValueError(f"{case.case_id}: candidate count mismatch")
        scores = query_scores[str(case.query_id)]
        actual_unknown = float(
            np.clip(1.0 - max(scores[item] for item in available), 0.0, 1.0)
        )
        fixed_unknown = float(
            np.clip(1.0 - max(scores[item] for item in candidate_ids), 0.0, 1.0)
        )
        for candidate_id in available:
            rows_candidate.append(
                {
                    "case_id": case.case_id,
                    "phase_id": candidate_id,
                    "score": scores[candidate_id],
                }
            )
            rows_candidate_fixed.append(
                {
                    "case_id": case.case_id,
                    "phase_id": candidate_id,
                    "score": scores[candidate_id],
                }
            )
        rows_case.append(
            {
                "case_id": case.case_id,
                "unknown_score": actual_unknown,
            }
        )
        rows_case_fixed.append(
            {
                "case_id": case.case_id,
                "unknown_score": fixed_unknown,
            }
        )

    args.outdir.mkdir(parents=True, exist_ok=False)
    outputs = {
        "candidate_predictions.csv": rows_candidate,
        "case_scores.csv": rows_case,
        "fixed_output_candidate_predictions.csv": rows_candidate_fixed,
        "fixed_output_case_scores.csv": rows_case_fixed,
    }
    for name, rows in outputs.items():
        frame = pd.DataFrame(rows)
        columns = ["case_id", "phase_id"] if "phase_id" in frame else ["case_id"]
        frame.sort_values(columns).to_csv(
            args.outdir / name,
            index=False,
            lineterminator="\n",
        )

    status = {
        "status": "precursor_genome_profile_baseline_complete",
        "method": "shifted Pearson profile correlation",
        "queries": len(queries),
        "cases": len(rows_case),
        "candidate_rows": len(rows_candidate),
        "libraries": len(cases_manifest["libraries"]),
        "shift_range_deg": [-0.30, 0.30],
        "shift_step_deg": 0.02,
        "candidate_predictions_sha256": sha256(
            args.outdir / "candidate_predictions.csv"
        ),
        "case_scores_sha256": sha256(args.outdir / "case_scores.csv"),
        "claim_boundary": (
            "Candidate scores are reference-only, so ranking is a positive "
            "control. Unknown evidence is recomputed from the deployed library."
        ),
    }
    (args.outdir / "execution_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
