#!/usr/bin/env python3
"""Repeat the Precursor Genome endpoint analysis on frozen subsets."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

SCORE_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCORE_SCRIPT_DIR))

from score_two_endpoints import score_method


def select_cases(
    cases: pd.DataFrame,
    truth: pd.DataFrame,
    predicate: Callable[[pd.Series], bool],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_cases = cases[cases.apply(predicate, axis=1)].copy()
    selected_truth = truth[
        truth["case_id"].isin(selected_cases["case_id"])
    ].copy()
    return selected_cases, selected_truth


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--query-manifest", type=Path, required=True)
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
    manifest = pd.read_csv(args.query_manifest, dtype=str)
    provenance = pd.read_csv(
        args.dataset / "evaluator" / "candidate_source_provenance.csv",
        dtype=str,
    )
    source_to_candidate = dict(
        zip(provenance["phase_id"], provenance["candidate_id"], strict=True)
    )
    quality_one_ids = set(
        manifest.loc[manifest["quality_score"].eq("1.0"), "sample_id"]
    )
    unreacted_ids = set(
        manifest.loc[manifest["reaction_category"].eq("unreacted"), "sample_id"]
    )
    phase_weights = {
        row.sample_id: {
            source_to_candidate[phase_id]: float(weight)
            for phase_id, weight in json.loads(
                row.phase_weights_json
            ).items()
        }
        for row in manifest.itertuples(index=False)
    }

    scenarios = {
        "quality_1": lambda row: row["query_id"] in quality_one_ids,
        "unreacted_only": lambda row: row["query_id"] in unreacted_ids,
        "omitted_weight_ge_005": lambda row: (
            row["condition"] != "omit_present"
            or phase_weights[row["query_id"]][row["omitted_phase_id"]] >= 0.05
        ),
    }

    methods = {
        "profile_baseline": args.profile_run,
        "crystalshift": args.crystalshift_run,
        "xdecomposer": args.xdecomposer_run,
    }
    args.outdir.mkdir(parents=True, exist_ok=False)
    summary: dict[str, object] = {
        "status": "precursor_genome_sensitivity_complete",
        "freeze": "SENSITIVITY_FREEZE_20261127.md",
        "scenarios": {},
    }

    for scenario_id, predicate in scenarios.items():
        selected_cases, selected_truth = select_cases(
            cases,
            truth,
            predicate,
        )
        if selected_cases.empty:
            raise ValueError(f"empty sensitivity scenario: {scenario_id}")
        scenario = {
            "queries": int(selected_cases["query_id"].nunique()),
            "clusters": int(selected_cases["cluster_id"].nunique()),
            "cases": len(selected_cases),
            "true_omission_cases": int(
                selected_cases["condition"].eq("omit_present").sum()
            ),
            "absent_omission_cases": int(
                selected_cases["condition"].eq("omit_absent").sum()
            ),
            "methods": {},
        }
        for method_id, run_dir in methods.items():
            card, _, _ = score_method(
                f"{method_id}_{scenario_id}",
                run_dir,
                selected_cases,
                selected_truth,
                args.bootstrap_repeats,
            )
            scenario["methods"][method_id] = {
                "ranking": card["ranking_endpoint"],
                "unknown": card["unknown_endpoint"],
                "bootstrap": card["cluster_bootstrap"]["intervals"],
            }
            (args.outdir / f"{scenario_id}_{method_id}.json").write_text(
                json.dumps(card, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        summary["scenarios"][scenario_id] = scenario
        print(
            json.dumps(
                {
                    scenario_id: {
                        "queries": scenario["queries"],
                        "cases": scenario["cases"],
                        "true_omission_cases": scenario[
                            "true_omission_cases"
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    (args.outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
