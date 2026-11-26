#!/usr/bin/env python3
"""Score the Precursor Genome two-endpoint panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

SCORE_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCORE_SCRIPT_DIR))

from score_two_endpoints import score_method


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--profile-run", type=Path, required=True)
    parser.add_argument("--crystalshift-run", type=Path, required=True)
    parser.add_argument("--xdecomposer-run", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--bootstrap-repeats", type=int, default=10_000)
    args = parser.parse_args()

    cases = pd.read_csv(args.cases / "cases.csv", dtype=str).fillna("")
    truth = pd.read_csv(
        args.cases / "case_phase_truth.csv",
        dtype={"case_id": str, "phase_id": str, "present": int},
    )
    args.outdir.mkdir(parents=True, exist_ok=False)
    scorecards = {}
    methods = (
        ("profile_baseline", args.profile_run),
        ("crystalshift", args.crystalshift_run),
        ("xdecomposer", args.xdecomposer_run),
    )
    for method_id, run_dir in methods:
        scorecard, ranking, unknown = score_method(
            method_id,
            run_dir,
            cases,
            truth,
            args.bootstrap_repeats,
        )
        scorecard["status"] = "precursor_genome_two_endpoint_method_scored"
        scorecard["claim_boundary"] = (
            "The source was already used in the project's closed-library "
            "benchmark. This panel is a new open-library intervention, not a "
            "fresh external source: 77/102 query IDs overlap the earlier "
            "cohort and 25 are new. Reference reactions are disjoint from query "
            "reactions; one active scan represents each physical reaction."
        )
        scorecards[method_id] = scorecard
        ranking.to_csv(
            args.outdir / f"{method_id}_ranking_cases.csv",
            index=False,
            lineterminator="\n",
        )
        unknown.to_csv(
            args.outdir / f"{method_id}_unknown_cases.csv",
            index=False,
            lineterminator="\n",
        )
        (args.outdir / f"{method_id}_scorecard.json").write_text(
            json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "status": "precursor_genome_two_endpoint_summary_complete",
        "source": "precursor_genome",
        "queries": len(cases["query_id"].unique()),
        "clusters": len(cases["cluster_id"].unique()),
        "cases": len(cases),
        "methods": scorecards,
        "cross_method_conclusion": (
            "No source-wide AUROC is pooled. Candidate-independent methods "
            "provide ranking controls, while library-dependent methods test "
            "whether the deployed residual changes."
        ),
    }
    (args.outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                method: {
                    "ranking": card["ranking_endpoint"],
                    "unknown": card["unknown_endpoint"],
                    "bootstrap": card["cluster_bootstrap"]["intervals"],
                }
                for method, card in scorecards.items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
