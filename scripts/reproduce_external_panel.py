"""Reproduce the frozen controlled external-method panel."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pxrd_complete_set_bench.evaluate import sha256
from pxrd_complete_set_bench.external_panel import (
    canonical_digest,
    evaluate_external_panel,
    load_predictions,
    load_registry,
    load_truth,
)

EXPECTED_TRUTH_SHA256 = (
    "70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b"
)
EXPECTED_PREDICTIONS_SHA256 = (
    "94826151d17b2ce3776329025e363e1734a142c0442269aaf75d50e4ff0162e1"
)
EXPECTED_RESULT_SHA256 = (
    "b39ba2b54526dbfee90863f5e25023e49f29c8c483adcc470a5d76015b14e4b5"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--truth",
        type=Path,
        default=REPO / "data" / "query_phase_scores.csv",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=REPO / "data" / "ariadnex_external_method_predictions.csv",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=REPO / "data" / "external_method_registry.json",
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=REPO / "results" / "ariadnex_external_panel.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    truth_digest = sha256(args.truth)
    prediction_digest = sha256(args.predictions)
    registry = load_registry(args.registry)
    method_ids = tuple(method["id"] for method in registry["methods"])
    started = time.perf_counter()
    actual = evaluate_external_panel(
        load_truth(args.truth),
        load_predictions(args.predictions, method_ids),
        registry,
        10_000,
        20261123,
    )
    actual["inputs"] = {
        "truth": {"file": str(args.truth), "sha256": truth_digest},
        "predictions": {
            "file": str(args.predictions),
            "sha256": prediction_digest,
        },
        "registry": {
            "file": str(args.registry),
            "sha256": sha256(args.registry),
        },
    }
    elapsed = time.perf_counter() - started
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    actual_digest = canonical_digest(actual)
    expected_digest = canonical_digest(expected)
    checks = {
        "truth_sha256": truth_digest == EXPECTED_TRUTH_SHA256,
        "predictions_sha256": prediction_digest == EXPECTED_PREDICTIONS_SHA256,
        "result_sha256": actual_digest == EXPECTED_RESULT_SHA256,
        "expected_result_sha256": expected_digest == EXPECTED_RESULT_SHA256,
        "result_matches_expected": actual_digest == expected_digest,
        "methods": len(actual["methods"]) == 6,
        "bootstrap": actual["contract"]["bootstrap_repeats"] == 10_000,
    }
    report = {
        "status": (
            "external_panel_reproduction_exact_match"
            if all(checks.values())
            else "external_panel_reproduction_failed"
        ),
        "truth_sha256": truth_digest,
        "predictions_sha256": prediction_digest,
        "actual_canonical_sha256": actual_digest,
        "expected_canonical_sha256": expected_digest,
        "elapsed_seconds": elapsed,
        "checks": checks,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
