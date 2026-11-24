"""Score a partial model submission against a frozen truth table."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.submission import score_submission


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budgets", default="1,2,3,4,5,10")
    parser.add_argument("--repeats", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261124)
    args = parser.parse_args()

    budgets = tuple(
        sorted({int(value) for value in args.budgets.split(",") if value.strip()})
    )
    truth = pd.read_csv(args.truth)
    predictions = pd.read_csv(args.predictions)
    report = score_submission(
        truth,
        predictions,
        budgets,
        args.repeats,
        args.seed,
    )
    report["inputs"] = {
        "truth": {
            "path": args.truth.as_posix(),
            "sha256": sha256(args.truth),
        },
        "predictions": {
            "path": args.predictions.as_posix(),
            "sha256": sha256(args.predictions),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "methods": sorted(report["methods"]),
                "sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
