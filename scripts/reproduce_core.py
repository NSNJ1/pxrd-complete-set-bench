"""Recompute the frozen benchmark result and compare canonical payloads."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pxrd_complete_set_bench.evaluate import evaluate, sha256

EXPECTED_INPUT_SHA256 = (
    "70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b"
)
EXPECTED_CORE_SHA256 = (
    "347e626c53642bd7acca100b10936a565e251b1d28fa2ce3407a0e466cf69069"
)


def canonical_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=REPO / "data" / "query_phase_scores.csv",
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=REPO / "results" / "evaluation_10000.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    input_digest = sha256(args.data)
    if input_digest != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"input SHA-256 mismatch: {input_digest} != {EXPECTED_INPUT_SHA256}"
        )

    frame = pd.read_csv(args.data)
    started = time.perf_counter()
    actual = evaluate(
        frame,
        "baseline_score",
        "method_score",
        (1, 2, 3, 4, 5, 10),
        10_000,
        20261118,
    )
    elapsed = time.perf_counter() - started
    actual["input"] = {
        "path": str(args.data.resolve()),
        "sha256": input_digest,
    }

    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    actual_compare = copy.deepcopy(actual)
    expected_compare = copy.deepcopy(expected)
    actual_compare.get("input", {}).pop("path", None)
    expected_compare.get("input", {}).pop("path", None)
    actual_digest = canonical_digest(actual_compare)
    expected_digest = canonical_digest(expected_compare)

    checks = {
        "input_sha256": input_digest == EXPECTED_INPUT_SHA256,
        "result_digest": actual_digest == expected_digest,
        "result_digest_expected": expected_digest == EXPECTED_CORE_SHA256,
        "sources": len(actual.get("sources", {})) == 7,
        "bootstrap": (
            actual.get("bootstrap", {}).get("repeats") == 10_000
            and actual.get("bootstrap", {}).get("seed") == 20261118
        ),
    }
    report = {
        "status": (
            "core_reproduction_exact_match"
            if all(checks.values())
            else "core_reproduction_failed"
        ),
        "input_sha256": input_digest,
        "actual_canonical_sha256": actual_digest,
        "expected_canonical_sha256": expected_digest,
        "elapsed_seconds": elapsed,
        "checks": checks,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
