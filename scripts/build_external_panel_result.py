"""Evaluate the controlled external-method panel and freeze the result."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pxrd_complete_set_bench.evaluate import sha256
from pxrd_complete_set_bench.external_panel import (
    canonical_digest,
    evaluate_external_panel,
    load_predictions,
    load_registry,
    load_truth,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap-repeats", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261123)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    method_ids = tuple(method["id"] for method in registry["methods"])
    started = time.perf_counter()
    report = evaluate_external_panel(
        load_truth(args.truth),
        load_predictions(args.predictions, method_ids),
        registry,
        repeats=args.bootstrap_repeats,
        seed=args.seed,
    )
    report["inputs"] = {
        "truth": {
            "file": args.truth.as_posix(),
            "sha256": sha256(args.truth),
        },
        "predictions": {
            "file": args.predictions.as_posix(),
            "sha256": sha256(args.predictions),
        },
        "registry": {
            "file": args.registry.as_posix(),
            "sha256": sha256(args.registry),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    elapsed = time.perf_counter() - started
    print(f"wrote {len(report['methods'])} methods to {args.out}")
    print(f"canonical_sha256={canonical_digest(report)}")
    print(f"elapsed_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
