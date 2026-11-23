"""Command-line interface for the PXRD complete-set review benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .diagnostics import DEFAULT_BUDGETS, DEFAULT_COVERAGES, DEFAULT_SIZES
from .diagnostics import DEFAULT_SEED as DIAGNOSTIC_SEED
from .diagnostics import run_diagnostics as compute_diagnostics
from .evaluate import evaluate, sha256
from .external_panel import (
    evaluate_external_panel,
    load_predictions,
    load_registry,
    load_truth,
)


def _budgets(value: str) -> tuple[int, ...]:
    budgets = tuple(sorted({int(item) for item in value.split(",") if item.strip()}))
    if not budgets or budgets[0] < 1:
        raise argparse.ArgumentTypeError("budgets must be positive integers")
    return budgets


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return number


def _methods(value: str) -> tuple[str, ...]:
    methods = tuple(item.strip() for item in value.split(",") if item.strip())
    if not methods:
        raise argparse.ArgumentTypeError("at least one method column is required")
    return methods


def _sizes(value: str) -> tuple[int | None, ...]:
    sizes = []
    for item in value.split(","):
        text = item.strip().lower()
        if not text:
            continue
        if text == "full":
            sizes.append(None)
            continue
        size = int(text)
        if size < 1:
            raise argparse.ArgumentTypeError("sizes must be positive or 'full'")
        sizes.append(size)
    if not sizes:
        raise argparse.ArgumentTypeError("at least one size is required")
    return tuple(sizes)


def _coverages(value: str) -> tuple[float, ...]:
    coverages = tuple(float(item) for item in value.split(",") if item.strip())
    if not coverages or any(not 0 < item <= 1 for item in coverages):
        raise argparse.ArgumentTypeError("coverages must be in (0, 1]")
    return coverages


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
        type=_positive_int,
        default=10_000,
    )
    evaluate_parser.add_argument(
        "--seed",
        type=int,
        default=20261118,
    )
    evaluate_parser.add_argument("--output-json", type=Path)

    panel_parser = subparsers.add_parser(
        "external-panel",
        help="evaluate the controlled eight-method comparison panel",
    )
    panel_parser.add_argument("truth", type=Path)
    panel_parser.add_argument("predictions", type=Path)
    panel_parser.add_argument("--registry", type=Path, required=True)
    panel_parser.add_argument(
        "--bootstrap-repeats",
        type=_positive_int,
        default=10_000,
    )
    panel_parser.add_argument("--seed", type=int, default=20261123)
    panel_parser.add_argument("--output-json", type=Path)

    diagnostics_parser = subparsers.add_parser(
        "diagnostics",
        help="analyze candidate-library scale, failure modes and abstention",
    )
    diagnostics_parser.add_argument("input", type=Path)
    diagnostics_parser.add_argument(
        "--methods",
        type=_methods,
        default=("baseline_score", "method_score"),
    )
    diagnostics_parser.add_argument(
        "--sizes",
        type=_sizes,
        default=DEFAULT_SIZES,
    )
    diagnostics_parser.add_argument(
        "--budgets",
        type=_budgets,
        default=DEFAULT_BUDGETS,
    )
    diagnostics_parser.add_argument("--review-budget", type=_positive_int, default=3)
    diagnostics_parser.add_argument(
        "--coverages",
        type=_coverages,
        default=DEFAULT_COVERAGES,
    )
    diagnostics_parser.add_argument(
        "--bootstrap-repeats",
        type=_positive_int,
        default=10_000,
    )
    diagnostics_parser.add_argument(
        "--sampling-replicates",
        type=_positive_int,
        default=20,
    )
    diagnostics_parser.add_argument("--seed", type=int, default=DIAGNOSTIC_SEED)
    diagnostics_parser.add_argument("--output-json", type=Path)
    diagnostics_parser.add_argument("--query-output", type=Path)
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
        args.output_json.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


def run_external_panel(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    method_ids = tuple(method["id"] for method in registry["methods"])
    truth = load_truth(args.truth)
    predictions = load_predictions(args.predictions, method_ids)
    report = evaluate_external_panel(
        truth,
        predictions,
        registry,
        args.bootstrap_repeats,
        args.seed,
    )
    report["inputs"] = {
        "truth": {
            "file": str(args.truth),
            "sha256": sha256(args.truth),
        },
        "predictions": {
            "file": str(args.predictions),
            "sha256": sha256(args.predictions),
        },
        "registry": {
            "file": str(args.registry),
            "sha256": sha256(args.registry),
        },
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


def run_diagnostics(args: argparse.Namespace) -> int:
    frame = pd.read_csv(args.input)
    report, query_output, _ = compute_diagnostics(
        frame,
        args.methods,
        args.sizes,
        args.budgets,
        args.review_budget,
        args.coverages,
        args.bootstrap_repeats,
        args.sampling_replicates,
        args.seed,
    )
    report["input"] = {
        "path": str(args.input),
        "sha256": sha256(args.input),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8", newline="\n")
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "sources": len(report["library_scaling"]),
                    "methods": list(args.methods),
                    "output": str(args.output_json),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(text, end="")
    if args.query_output is not None:
        args.query_output.parent.mkdir(parents=True, exist_ok=True)
        query_text = query_output.sort_values(["source", "query_id", "method"]).to_csv(
            index=False, lineterminator="\n"
        )
        args.query_output.write_bytes(query_text.encode())
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evaluate":
        return run_evaluate(args)
    if args.command == "external-panel":
        return run_external_panel(args)
    if args.command == "diagnostics":
        return run_diagnostics(args)
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
