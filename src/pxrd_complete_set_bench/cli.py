"""Command-line interface for the PXRD complete-set review benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .evaluate import evaluate, sha256


def _budgets(value: str) -> tuple[int, ...]:
    budgets = tuple(sorted({int(item) for item in value.split(",") if item.strip()}))
    if not budgets or budgets[0] < 1:
        raise argparse.ArgumentTypeError("budgets must be positive integers")
    return budgets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pxrd-complete-set-bench",
        description=(
            "Evaluate complete-phase-set retrieval under a fixed review budget."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="evaluate a query-phase score table",
    )
    evaluate_parser.add_argument("input", type=Path)
    evaluate_parser.add_argument(
        "--baseline-column",
        default="baseline_score",
    )
    evaluate_parser.add_argument(
        "--method-column",
        default="method_score",
    )
    evaluate_parser.add_argument(
        "--budgets",
        type=_budgets,
        default=(1, 2, 3, 4, 5, 10),
    )
    evaluate_parser.add_argument(
        "--bootstrap-repeats",
        type=int,
        default=10_000,
    )
    evaluate_parser.add_argument(
        "--seed",
        type=int,
        default=20261118,
    )
    evaluate_parser.add_argument("--output-json", type=Path)
    return parser


def run_evaluate(args: argparse.Namespace) -> int:
    frame = pd.read_csv(args.input)
    report = evaluate(
        frame,
        args.baseline_column,
        args.method_column,
        args.budgets,
        args.bootstrap_repeats,
        args.seed,
    )
    report["input"] = {
        "path": str(args.input.resolve()),
        "sha256": sha256(args.input),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evaluate":
        return run_evaluate(args)
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
