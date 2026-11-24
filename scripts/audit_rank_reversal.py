"""Audit endpoint-dependent method ranks on the controlled PXRD panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.rank_reversal import rank_reversal_report


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--budgets", default="1,2,3,4")
    parser.add_argument("--repeats", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261123)
    args = parser.parse_args()

    budgets = tuple(
        sorted({int(value) for value in args.budgets.split(",") if value.strip()})
    )
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    method_ids = tuple(method["id"] for method in registry["methods"])
    frame = pd.read_csv(args.scores)
    report = rank_reversal_report(
        frame,
        method_ids,
        budgets,
        args.repeats,
        args.seed,
    )
    report["inputs"] = {
        "scores": {
            "path": args.scores.as_posix(),
            "sha256": sha256(args.scores),
        },
        "registry": {
            "path": args.registry.as_posix(),
            "sha256": sha256(args.registry),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "headline": report["headline"],
                "aggregate_pairwise_reversal_fraction": report[
                    "aggregate_pairwise_reversal_fraction"
                ],
                "output_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
