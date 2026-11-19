"""Source-stratified evaluation for complete-set PXRD review."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

REQUIRED_COLUMNS = {
    "source",
    "query_id",
    "cluster_id",
    "phase_id",
    "present",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    frame: pd.DataFrame,
    baseline: str,
    method: str,
) -> None:
    missing = REQUIRED_COLUMNS | {baseline, method}
    absent = missing - set(frame.columns)
    if absent:
        raise ValueError(f"missing columns: {sorted(absent)}")
    if frame[["source", "query_id", "cluster_id", "phase_id"]].isna().any().any():
        raise ValueError("source/query/cluster/phase identity contains null")
    if frame.duplicated(["source", "query_id", "phase_id"]).any():
        raise ValueError("duplicate source/query/phase rows")
    if (
        not frame[["present", baseline, method]]
        .apply(lambda column: np.isfinite(column.astype(float)).all())
        .all()
    ):
        raise ValueError("present/scores contain non-finite values")
    if not frame["present"].isin([0, 1]).all():
        raise ValueError("present must be binary")
    if "primary" in frame.columns:
        valid_primary = frame["primary"].dropna()
        if not valid_primary.isin([0, 1]).all():
            raise ValueError("primary must be binary or blank")

    grouped = frame.groupby(["source", "query_id"], sort=False)
    if (grouped["cluster_id"].nunique() != 1).any():
        raise ValueError("each query must belong to exactly one cluster")
    if (grouped["present"].sum() < 1).any():
        raise ValueError("every query needs at least one positive phase")
    if "primary" in frame.columns:
        counts = grouped["primary"].sum(min_count=1)
        if not counts.dropna().isin([0, 1]).all():
            raise ValueError("each labelled query needs at most one primary")


def cluster_bootstrap_rate(
    queries: pd.DataFrame,
    treatment: str,
    baseline: str,
    repeats: int,
    seed: int,
) -> dict:
    queries = queries.reset_index(drop=True)
    delta = queries[treatment].to_numpy(dtype=np.float64) - queries[baseline].to_numpy(
        dtype=np.float64
    )
    groups = {
        cluster: group.index.to_numpy()
        for cluster, group in queries.groupby("cluster_id", sort=True)
    }
    labels = sorted(groups)
    rng = np.random.default_rng(seed)
    samples = np.empty(repeats, dtype=np.float64)
    for repeat in range(repeats):
        selected = rng.choice(labels, len(labels), replace=True)
        indices = np.concatenate([groups[label] for label in selected])
        samples[repeat] = float(delta[indices].mean())
    return {
        "estimate": float(delta.mean()),
        "ci95": [
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        ],
        "clusters": len(labels),
        "queries": len(queries),
    }


def cluster_bootstrap_ap(
    pairs: pd.DataFrame,
    treatment: str,
    baseline: str,
    repeats: int,
    seed: int,
) -> dict:
    pairs = pairs.reset_index(drop=True)
    groups = {
        cluster: group.index.to_numpy()
        for cluster, group in pairs.groupby("cluster_id", sort=True)
    }
    labels = sorted(groups)
    present = pairs["present"].to_numpy(dtype=np.int64)
    treatment_values = pairs[treatment].to_numpy(dtype=np.float64)
    baseline_values = pairs[baseline].to_numpy(dtype=np.float64)
    rng = np.random.default_rng(seed)
    samples = np.empty(repeats, dtype=np.float64)
    for repeat in range(repeats):
        selected = rng.choice(labels, len(labels), replace=True)
        indices = np.concatenate([groups[label] for label in selected])
        samples[repeat] = average_precision_score(
            present[indices], treatment_values[indices]
        ) - average_precision_score(present[indices], baseline_values[indices])
    return {
        "estimate": float(
            average_precision_score(present, treatment_values)
            - average_precision_score(present, baseline_values)
        ),
        "ci95": [
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        ],
        "clusters": len(labels),
        "queries": int(pairs["query_id"].nunique()),
    }


def rank_queries(
    frame: pd.DataFrame,
    score_column: str,
    budgets: tuple[int, ...],
) -> pd.DataFrame:
    rows = []
    for (source, query_id), group in frame.groupby(
        ["source", "query_id"],
        sort=False,
    ):
        ordered = group.sort_values(
            score_column,
            ascending=False,
            kind="stable",
        )
        present = ordered["present"].to_numpy(dtype=np.int64)
        positive_count = int(present.sum())
        true_set = "|".join(sorted(ordered.loc[ordered["present"].eq(1), "phase_id"]))
        row = {
            "source": source,
            "query_id": query_id,
            "cluster_id": ordered["cluster_id"].iloc[0],
            "phase_count": positive_count,
            "true_set": true_set,
            "candidate_count": len(ordered),
            "phase_ap": (
                float(
                    average_precision_score(
                        present,
                        ordered[score_column],
                    )
                )
                if len(np.unique(present)) == 2
                else math.nan
            ),
            "top1_present": float(present[0] == 1),
        }
        if "primary" in ordered.columns and ordered["primary"].notna().any():
            primary_mask = ordered["primary"].fillna(0).to_numpy(dtype=np.int64)
            row["dominant_top1"] = float(primary_mask[0] == 1)
        for k in budgets:
            row[f"all_present_at_{k}"] = float(present[:k].sum() == positive_count)
        rows.append(row)
    return pd.DataFrame(rows)


def screen_diagnostics(
    source_pairs: pd.DataFrame,
    baseline: str,
    method: str,
    budgets: tuple[int, ...],
    repeats: int,
    seed: int,
) -> dict:
    reports = {}
    for budget in budgets:
        rows = []
        for (source, query_id), group in source_pairs.groupby(
            ["source", "query_id"],
            sort=False,
        ):
            positive_count = int(group["present"].sum())
            if positive_count < 1:
                continue
            baseline_order = group.sort_values(
                baseline,
                ascending=False,
                kind="stable",
            )
            method_order = group.sort_values(
                method,
                ascending=False,
                kind="stable",
            )
            baseline_screen = baseline_order.head(budget)
            method_screen = method_order.head(budget)
            screen_ids = set(baseline_screen["phase_id"])
            same_screen = group[group["phase_id"].isin(screen_ids)]
            baseline_recall = float(baseline_screen["present"].sum()) / positive_count
            method_recall = float(method_screen["present"].sum()) / positive_count
            row = {
                "source": source,
                "query_id": query_id,
                "cluster_id": group["cluster_id"].iloc[0],
                "baseline_true_phase_recall": baseline_recall,
                "method_true_phase_recall": method_recall,
                "baseline_complete_set_eligible": float(baseline_recall == 1.0),
                "method_complete_set_eligible": float(method_recall == 1.0),
                "same_screen_phase_ap_baseline": math.nan,
                "same_screen_phase_ap_method": math.nan,
            }
            screen_present = same_screen["present"].to_numpy(dtype=np.int64)
            if len(np.unique(screen_present)) == 2:
                row["same_screen_phase_ap_baseline"] = float(
                    average_precision_score(
                        screen_present,
                        same_screen[baseline],
                    )
                )
                row["same_screen_phase_ap_method"] = float(
                    average_precision_score(
                        screen_present,
                        same_screen[method],
                    )
                )
            rows.append(row)
        diagnostics = pd.DataFrame(rows)
        screened = diagnostics.dropna(
            subset=[
                "same_screen_phase_ap_baseline",
                "same_screen_phase_ap_method",
            ]
        )
        reports[str(budget)] = {
            "queries": len(diagnostics),
            "clusters": int(diagnostics["cluster_id"].nunique()),
            "true_phase_recall": {
                "baseline": float(diagnostics["baseline_true_phase_recall"].mean()),
                "method": float(diagnostics["method_true_phase_recall"].mean()),
                "paired_delta": cluster_bootstrap_rate(
                    diagnostics,
                    "method_true_phase_recall",
                    "baseline_true_phase_recall",
                    repeats,
                    seed,
                ),
            },
            "complete_set_eligibility": {
                "baseline": float(diagnostics["baseline_complete_set_eligible"].mean()),
                "method": float(diagnostics["method_complete_set_eligible"].mean()),
                "paired_delta": cluster_bootstrap_rate(
                    diagnostics,
                    "method_complete_set_eligible",
                    "baseline_complete_set_eligible",
                    repeats,
                    seed,
                ),
            },
            "same_baseline_screen_phase_ap_macro": {
                "queries": len(screened),
                "baseline": (
                    float(screened["same_screen_phase_ap_baseline"].mean())
                    if len(screened)
                    else None
                ),
                "method": (
                    float(screened["same_screen_phase_ap_method"].mean())
                    if len(screened)
                    else None
                ),
                "paired_delta": (
                    cluster_bootstrap_rate(
                        screened,
                        "same_screen_phase_ap_method",
                        "same_screen_phase_ap_baseline",
                        repeats,
                        seed,
                    )
                    if len(screened)
                    else None
                ),
            },
        }
    return reports


def summarize(
    queried: pd.DataFrame,
    pairs: pd.DataFrame,
    column: str,
    budgets: tuple[int, ...],
) -> dict:
    result = {
        "queries": len(queried),
        "clusters": int(queried["cluster_id"].nunique()),
        "phase_ap_micro": float(
            average_precision_score(pairs["present"], pairs[column])
        ),
        "phase_ap_macro": float(queried["phase_ap"].mean()),
        "top1_present": float(queried["top1_present"].mean()),
    }
    if "dominant_top1" in queried.columns:
        result["dominant_top1"] = float(queried["dominant_top1"].mean())
    else:
        result["dominant_top1"] = None

    exact_set_weights = queried.groupby("true_set", sort=False).size().to_dict()
    cardinality_weights = queried.groupby("phase_count", sort=False).size().to_dict()
    for k in budgets:
        key = f"all_present_at_{k}"
        result[key] = float(queried[key].mean())
        result[f"{key}_set_macro"] = float(
            np.mean(
                [
                    group[key].mean()
                    for _, group in queried.groupby(
                        "true_set",
                        sort=False,
                    )
                ]
            )
        )
        result[f"{key}_cardinality_balanced"] = float(
            np.mean(
                [
                    group[key].mean()
                    for _, group in queried.groupby(
                        "phase_count",
                        sort=False,
                    )
                ]
            )
        )
    result["exact_set_clusters"] = len(exact_set_weights)
    result["cardinality_strata"] = len(cardinality_weights)
    result["cardinality_results"] = {}
    for phase_count, group in queried.groupby("phase_count", sort=True):
        query_ids = set(group["query_id"])
        stratum_pairs = pairs[pairs["query_id"].isin(query_ids)]
        row = {
            "queries": len(group),
            "clusters": int(group["cluster_id"].nunique()),
            "phase_ap_micro": float(
                average_precision_score(
                    stratum_pairs["present"],
                    stratum_pairs[column],
                )
            ),
            "phase_ap_macro": float(group["phase_ap"].mean()),
            "top1_present": float(group["top1_present"].mean()),
            "dominant_top1": (
                float(group["dominant_top1"].mean())
                if "dominant_top1" in group.columns
                else None
            ),
        }
        for k in budgets:
            row[f"all_present_at_{k}"] = float(group[f"all_present_at_{k}"].mean())
        result["cardinality_results"][str(int(phase_count))] = row
    return result


def cardinality_paired_deltas(
    source_pairs: pd.DataFrame,
    combined_queries: pd.DataFrame,
    baseline: str,
    method: str,
    budgets: tuple[int, ...],
    repeats: int,
    seed: int,
) -> dict:
    reports = {}
    for phase_count, queries in combined_queries.groupby(
        "phase_count",
        sort=True,
    ):
        query_ids = set(queries["query_id"])
        stratum_pairs = source_pairs[source_pairs["query_id"].isin(query_ids)]
        report = {
            "queries": len(queries),
            "clusters": int(queries["cluster_id"].nunique()),
            "phase_ap_micro": cluster_bootstrap_ap(
                stratum_pairs,
                method,
                baseline,
                repeats,
                seed,
            ),
            "top1_present": cluster_bootstrap_rate(
                queries,
                "top1_present__method",
                "top1_present__baseline",
                repeats,
                seed,
            ),
        }
        if "dominant_top1__method" in queries:
            labelled = queries.dropna(
                subset=[
                    "dominant_top1__method",
                    "dominant_top1__baseline",
                ]
            )
            if not labelled.empty:
                report["dominant_top1"] = cluster_bootstrap_rate(
                    labelled,
                    "dominant_top1__method",
                    "dominant_top1__baseline",
                    repeats,
                    seed,
                )
            else:
                report["dominant_top1"] = None
        for k in budgets:
            report[f"all_present_at_{k}"] = cluster_bootstrap_rate(
                queries,
                f"all_present_at_{k}__method",
                f"all_present_at_{k}__baseline",
                repeats,
                seed,
            )
        reports[str(int(phase_count))] = report
    return reports


def evaluate(
    frame: pd.DataFrame,
    baseline: str,
    method: str,
    budgets: tuple[int, ...],
    repeats: int,
    seed: int,
) -> dict:
    validate(frame, baseline, method)
    source_reports = {}
    for source, source_frame in frame.groupby("source", sort=True):
        baseline_queries = rank_queries(
            source_frame,
            baseline,
            budgets,
        )
        method_queries = rank_queries(
            source_frame,
            method,
            budgets,
        )
        baseline_queries = baseline_queries.rename(
            columns={
                column: f"{column}__baseline"
                for column in baseline_queries.columns
                if column
                in {
                    "phase_ap",
                    "top1_present",
                    "dominant_top1",
                    *(f"all_present_at_{k}" for k in budgets),
                }
            }
        )
        method_queries = method_queries.rename(
            columns={
                column: f"{column}__method"
                for column in method_queries.columns
                if column
                in {
                    "phase_ap",
                    "top1_present",
                    "dominant_top1",
                    *(f"all_present_at_{k}" for k in budgets),
                }
            }
        )
        keys = ["source", "query_id", "cluster_id", "phase_count"]
        combined_queries = baseline_queries[
            keys
            + [
                column
                for column in baseline_queries.columns
                if column.endswith("__baseline")
            ]
        ].merge(
            method_queries[
                keys
                + [
                    column
                    for column in method_queries.columns
                    if column.endswith("__method")
                ]
            ],
            on=keys,
            validate="one_to_one",
        )
        source_pairs = source_frame.copy()
        deltas = {
            "phase_ap_micro": cluster_bootstrap_ap(
                source_pairs,
                method,
                baseline,
                repeats,
                seed,
            ),
            "top1_present": cluster_bootstrap_rate(
                combined_queries,
                "top1_present__method",
                "top1_present__baseline",
                repeats,
                seed,
            ),
        }
        if "dominant_top1__method" in combined_queries:
            deltas["dominant_top1"] = cluster_bootstrap_rate(
                combined_queries.dropna(
                    subset=[
                        "dominant_top1__method",
                        "dominant_top1__baseline",
                    ]
                ),
                "dominant_top1__method",
                "dominant_top1__baseline",
                repeats,
                seed,
            )
        for k in budgets:
            deltas[f"all_present_at_{k}"] = cluster_bootstrap_rate(
                combined_queries,
                f"all_present_at_{k}__method",
                f"all_present_at_{k}__baseline",
                repeats,
                seed,
            )
        source_reports[source] = {
            "baseline": summarize(
                baseline_queries.rename(
                    columns={
                        column: column.removesuffix("__baseline")
                        for column in baseline_queries.columns
                    }
                ),
                source_pairs,
                baseline,
                budgets,
            ),
            "method": summarize(
                method_queries.rename(
                    columns={
                        column: column.removesuffix("__method")
                        for column in method_queries.columns
                    }
                ),
                source_pairs,
                method,
                budgets,
            ),
            "paired_deltas": deltas,
            "cardinality_paired_deltas": cardinality_paired_deltas(
                source_pairs,
                combined_queries,
                baseline,
                method,
                budgets,
                repeats,
                seed,
            ),
            "screen_diagnostics": screen_diagnostics(
                source_pairs,
                baseline,
                method,
                budgets,
                repeats,
                seed,
            ),
        }
    return {
        "status": "complete_set_evaluation",
        "baseline_column": baseline,
        "method_column": method,
        "budgets": list(budgets),
        "bootstrap": {
            "cluster_column": "cluster_id",
            "repeats": repeats,
            "seed": seed,
        },
        "sources": source_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--baseline-column", default="baseline_score")
    parser.add_argument("--method-column", default="method_score")
    parser.add_argument("--budgets", default="1,2,3,4,5,10")
    parser.add_argument("--bootstrap-repeats", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()

    budgets = tuple(
        sorted({int(value) for value in args.budgets.split(",") if value.strip()})
    )
    if not budgets or budgets[0] < 1:
        raise ValueError("budgets must be positive")
    frame = pd.read_csv(args.input)
    report = evaluate(
        frame,
        args.baseline_column,
        args.method_column,
        budgets,
        args.bootstrap_repeats,
        args.seed,
    )
    report["input"] = {
        "path": str(args.input.resolve()),
        "sha256": sha256(args.input),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_json:
        args.output_json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
