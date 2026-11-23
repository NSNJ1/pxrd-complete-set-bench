"""Reproduce the frozen candidate-library and risk diagnostics."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.diagnostics import run_diagnostics
from pxrd_complete_set_bench.evaluate import sha256

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


EXPECTED_INPUT_SHA256 = (
    "70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b"
)
EXPECTED_QUERY_SHA256 = (
    "7c5a2460e23c1e98328cf2d9b139abd96bb91b74d9442a21c723b3dc07c1d29b"
)
EXPECTED_RESULT_SHA256 = (
    "db1066bed3931ff668b7b24f4ecca6b238f3a897458eab3ce1d3fd09c0fe7598"
)


def canonical_digest(payload: dict) -> str:
    payload = copy.deepcopy(payload)
    input_metadata = payload.get("input")
    if isinstance(input_metadata, dict):
        input_metadata.pop("path", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=REPO / "data" / "query_phase_scores.csv",
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=REPO / "results" / "diagnostics_10000.json",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--query-output", type=Path)
    args = parser.parse_args()

    input_digest = sha256(args.input)
    if input_digest != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"input SHA-256 mismatch: {input_digest} != {EXPECTED_INPUT_SHA256}"
        )
    frame = pd.read_csv(args.input)
    started = time.perf_counter()
    report, query_records, _ = run_diagnostics(
        frame,
        ("baseline_score", "method_score"),
        sizes=(4, 10, 20, 50, 100, None),
        budgets=(1, 2, 3, 5, 10),
        review_budget=3,
        coverages=(0.5, 0.7, 0.9, 1.0),
        bootstrap_repeats=10_000,
        sampling_replicates=20,
        seed=20261118,
    )
    elapsed = time.perf_counter() - started
    query_records = query_records.sort_values(
        ["source", "query_id", "method"]
    ).reset_index(drop=True)
    query_text = query_records.to_csv(index=False, lineterminator="\n")
    query_digest = hashlib.sha256(query_text.encode()).hexdigest()
    report["input"] = {
        "path": str(args.input),
        "sha256": input_digest,
    }

    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    actual_digest = canonical_digest(report)
    expected_digest = canonical_digest(expected)
    checks = {
        "input_sha256": input_digest == EXPECTED_INPUT_SHA256,
        "query_sha256": query_digest == EXPECTED_QUERY_SHA256,
        "result_sha256": actual_digest == EXPECTED_RESULT_SHA256,
        "expected_result_sha256": expected_digest == EXPECTED_RESULT_SHA256,
        "result_matches_expected": actual_digest == expected_digest,
        "sources": len(report["library_scaling"]) == 7,
        "bootstrap": report["contract"]["bootstrap_repeats"] == 10_000,
    }
    result = {
        "status": (
            "diagnostics_reproduction_exact_match"
            if all(checks.values())
            else "diagnostics_reproduction_failed"
        ),
        "input_sha256": input_digest,
        "query_records_sha256": query_digest,
        "actual_canonical_sha256": actual_digest,
        "expected_canonical_sha256": expected_digest,
        "elapsed_seconds": elapsed,
        "checks": checks,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(text, end="")
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            text,
            encoding="utf-8",
            newline="\n",
        )
    if args.query_output is not None:
        args.query_output.parent.mkdir(parents=True, exist_ok=True)
        args.query_output.write_text(
            query_text,
            encoding="utf-8",
            newline="\n",
        )
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
