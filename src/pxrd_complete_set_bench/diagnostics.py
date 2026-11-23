"""Mechanism diagnostics for complete-set PXRD retrieval."""

from __future__ import annotations

import hashlib
import math
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from .evaluate import REQUIRED_COLUMNS

DEFAULT_SIZES = (4, 10, 20, 50, 100, None)
DEFAULT_BUDGETS = (1, 2, 3, 5, 10)
DEFAULT_COVERAGES = (0.5, 0.7, 0.9, 1.0)
DEFAULT_SEED = 20261118
DEFAULT_SAMPLING_REPLICATES = 20
FAILURE_CATEGORIES = (
    "complete_set_success",
    "boundary_tie_failure",
    "single_rank_near_miss",
    "shallow_omission",
    "deep_omission",
)


def _mean_or_none(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _validate(frame: pd.DataFrame, methods: tuple[str, ...]) -> None:
    missing = REQUIRED_COLUMNS | set(methods)
    absent = missing - set(frame.columns)
    if absent:
        raise ValueError(f"missing columns: {sorted(absent)}")
    if frame.duplicated(["source", "query_id", "phase_id"]).any():
        raise ValueError("duplicate source/query/phase rows")
    if not frame["present"].isin([0, 1]).all():
        raise ValueError("present must be binary")
    if not np.isfinite(frame[list(methods)].to_numpy(dtype=float)).all():
        raise ValueError("scores must be finite")
    grouped = frame.groupby(["source", "query_id"])
    if grouped["present"].sum().lt(1).any():
        raise ValueError("every query needs at least one present phase")
    if grouped["cluster_id"].nunique().ne(1).any():
        raise ValueError("each query must use exactly one cluster")


def _stable_rank(group: pd.DataFrame, method: str) -> pd.DataFrame:
    return group.sort_values(
        [method, "phase_id"],
        ascending=[False, True],
        kind="stable",
    )


def _seed_for_library(seed: int, source: str, query: str, size: int) -> int:
    payload = f"{seed}|{source}|{query}|{size}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def sample_nested_library(
    group: pd.DataFrame,
    target_size: int,
    seed: int,
) -> pd.DataFrame | None:
    """Keep all positives and sample only unlabelled candidate negatives."""
    if target_size < 1:
        raise ValueError("target_size must be positive")
    positives = group.loc[group["present"].eq(1)]
    negatives = group.loc[group["present"].eq(0)].sort_values("phase_id")
    if target_size < len(positives):
        return None
    if target_size >= len(group):
        return group
    source = str(group["source"].iloc[0])
    query = str(group["query_id"].iloc[0])
    rng = np.random.default_rng(_seed_for_library(seed, source, query, target_size))
    selected_negatives = rng.choice(
        negatives["phase_id"].to_numpy(),
        size=target_size - len(positives),
        replace=False,
    )
    selected = set(positives["phase_id"]) | set(selected_negatives.tolist())
    return group.loc[group["phase_id"].isin(selected)]


def _query_metrics(
    group: pd.DataFrame,
    method: str,
    budgets: tuple[int, ...],
) -> dict:
    ranked = _stable_rank(group, method)
    present = ranked["present"].to_numpy(dtype=np.int8)
    scores = ranked[method].to_numpy(dtype=np.float64)
    positive_count = int(present.sum())
    positive_ranks = np.flatnonzero(present) + 1
    result = {
        "candidate_count": len(ranked),
        "phase_count": positive_count,
        "phase_ap": (
            float(average_precision_score(present, scores))
            if len(np.unique(present)) == 2
            else math.nan
        ),
        "minimum_positive_rank": int(positive_ranks.min()),
        "maximum_positive_rank": int(positive_ranks.max()),
        "top1_present": float(present[0] == 1),
    }
    for budget in budgets:
        available = min(budget, len(ranked))
        result[f"all_present_at_{budget}"] = float(
            int(present[:available].sum()) == positive_count
        )
        result[f"screening_recall_at_{budget}"] = float(
            present[:available].sum() / positive_count
        )
    return result


def _cluster_bootstrap_mean(
    records: pd.DataFrame,
    value_column: str,
    repeats: int,
    seed: int,
) -> list[float] | None:
    values = records[[value_column, "cluster_id"]].dropna()
    if values.empty:
        return None
    clusters = sorted(values["cluster_id"].unique())
    cluster_sums = np.asarray(
        [
            values.loc[values["cluster_id"].eq(cluster), value_column].sum()
            for cluster in clusters
        ]
    )
    cluster_counts = np.asarray(
        [
            values.loc[values["cluster_id"].eq(cluster), value_column].count()
            for cluster in clusters
        ]
    )
    rng = np.random.default_rng(seed)
    selected = rng.integers(0, len(clusters), size=(repeats, len(clusters)))
    sums = cluster_sums[selected].sum(axis=1)
    counts = cluster_counts[selected].sum(axis=1)
    samples = np.divide(
        sums,
        counts,
        out=np.full(repeats, np.nan),
        where=counts > 0,
    )
    samples = samples[np.isfinite(samples)]
    if not len(samples):
        return None
    return [
        float(np.quantile(samples, 0.025)),
        float(np.quantile(samples, 0.975)),
    ]


def _summarize_metric(
    records: pd.DataFrame,
    column: str,
    repeats: int,
    seed: int,
    bootstrap: bool,
) -> dict:
    replicate_means = records.groupby("replicate", sort=True)[column].mean().dropna()
    if replicate_means.empty:
        return {
            "mean": None,
            "replicate_min": None,
            "replicate_max": None,
            "ci95": None,
        }
    per_query = (
        records.groupby(["query_id", "cluster_id"], sort=True)[column]
        .mean()
        .reset_index()
    )
    ci = (
        _cluster_bootstrap_mean(per_query, column, repeats, seed) if bootstrap else None
    )
    return {
        "mean": float(replicate_means.mean()),
        "replicate_min": float(replicate_means.min()),
        "replicate_max": float(replicate_means.max()),
        "ci95": ci,
    }


def _library_scaling(
    frame: pd.DataFrame,
    methods: tuple[str, ...],
    sizes: tuple[int | None, ...],
    budgets: tuple[int, ...],
    sampling_replicates: int,
    bootstrap_repeats: int,
    seed: int,
) -> tuple[dict, dict]:
    source_reports = {}
    source_balanced = {method: {} for method in methods}
    for source, source_frame in frame.groupby("source", sort=True):
        queries = {
            query: group for query, group in source_frame.groupby("query_id", sort=True)
        }
        source_reports[str(source)] = {method: {} for method in methods}
        for requested_size in sizes:
            key = "full" if requested_size is None else str(requested_size)
            records = []
            eligible_queries = [
                query
                for query, group in queries.items()
                if requested_size is None
                or (
                    requested_size <= len(group)
                    and requested_size >= int(group["present"].sum())
                )
            ]
            if not eligible_queries:
                continue
            replicate_count = 1 if requested_size is None else sampling_replicates
            for replicate in range(replicate_count):
                for query in eligible_queries:
                    group = queries[query]
                    target = len(group) if requested_size is None else requested_size
                    if target >= len(group):
                        subset = group
                    else:
                        source_name = str(source)
                        rng = np.random.default_rng(
                            _seed_for_library(
                                seed,
                                source_name,
                                str(query),
                                target + replicate * 1_000_003,
                            )
                        )
                        positives = group.loc[group["present"].eq(1)]
                        negatives = group.loc[group["present"].eq(0)].sort_values(
                            "phase_id"
                        )
                        selected_negatives = rng.choice(
                            negatives["phase_id"].to_numpy(),
                            size=target - len(positives),
                            replace=False,
                        )
                        selected = set(positives["phase_id"]) | set(
                            selected_negatives.tolist()
                        )
                        subset = group.loc[group["phase_id"].isin(selected)]
                    for method in methods:
                        values = _query_metrics(subset, method, budgets)
                        records.append(
                            {
                                "source": source,
                                "query_id": query,
                                "cluster_id": group["cluster_id"].iloc[0],
                                "replicate": replicate,
                                "method": method,
                                **values,
                            }
                        )
            local = pd.DataFrame(records)
            for method in methods:
                method_rows = local.loc[local["method"].eq(method)]
                if method_rows.empty:
                    continue
                endpoints = (
                    "phase_ap",
                    *(f"all_present_at_{budget}" for budget in budgets),
                    *(f"screening_recall_at_{budget}" for budget in budgets),
                )
                metrics = {
                    endpoint: _summarize_metric(
                        method_rows,
                        endpoint,
                        bootstrap_repeats,
                        seed,
                        bootstrap=endpoint
                        in {
                            "phase_ap",
                            "all_present_at_3",
                            "screening_recall_at_3",
                        },
                    )
                    for endpoint in endpoints
                }
                source_reports[str(source)][method][key] = {
                    "requested_size": requested_size,
                    "queries": len(eligible_queries),
                    "query_coverage_fraction": (len(eligible_queries) / len(queries)),
                    "sampling_replicates": replicate_count,
                    "mean_candidate_count": float(
                        method_rows["candidate_count"].mean()
                    ),
                    **metrics,
                }
    for method in methods:
        size_keys = sorted(
            {size for report in source_reports.values() for size in report[method]},
            key=lambda item: float("inf") if item == "full" else int(item),
        )
        for size in size_keys:
            available = [
                report[method][size]
                for report in source_reports.values()
                if size in report[method]
            ]
            ap_values = [
                row["phase_ap"]["mean"]
                for row in available
                if row["phase_ap"]["mean"] is not None
            ]
            source_balanced[method][size] = {
                "sources": len(available),
                "phase_ap_macro": _mean_or_none(ap_values),
                **{
                    f"all_present_at_{budget}": _mean_or_none(
                        [
                            row[f"all_present_at_{budget}"]["mean"]
                            for row in available
                            if row[f"all_present_at_{budget}"]["mean"] is not None
                        ]
                    )
                    for budget in budgets
                },
            }
    return source_reports, source_balanced


def _failure_category(
    group: pd.DataFrame,
    method: str,
    budget: int,
) -> tuple[str, dict]:
    ranked = _stable_rank(group, method)
    present = ranked["present"].to_numpy(dtype=np.int8)
    scores = ranked[method].to_numpy(dtype=np.float64)
    available = min(budget, len(ranked))
    if int(present[:available].sum()) == int(present.sum()):
        category = "complete_set_success"
    else:
        missing_ranks = np.flatnonzero(present[available:]) + available + 1
        if len(ranked) > budget and scores[budget - 1] == scores[budget]:
            category = "boundary_tie_failure"
        elif int(missing_ranks.max()) == budget + 1:
            category = "single_rank_near_miss"
        elif int(missing_ranks.max()) <= budget + 3:
            category = "shallow_omission"
        else:
            category = "deep_omission"
    positive_ranks = np.flatnonzero(present) + 1
    return category, {
        "worst_positive_rank": int(positive_ranks.max()),
        "rank_gap": max(int(positive_ranks.max()) - budget, 0),
        "missing_positive_count": max(
            int(present.sum()) - int(present[:available].sum()),
            0,
        ),
    }


def _failure_taxonomy(
    frame: pd.DataFrame,
    methods: tuple[str, ...],
    review_budget: int,
) -> tuple[dict, pd.DataFrame]:
    rows = []
    for (source, query), group in frame.groupby(
        ["source", "query_id"],
        sort=True,
    ):
        for method in methods:
            category, details = _failure_category(
                group,
                method,
                review_budget,
            )
            rows.append(
                {
                    "source": source,
                    "query_id": query,
                    "cluster_id": group["cluster_id"].iloc[0],
                    "method": method,
                    "phase_count": int(group["present"].sum()),
                    "candidate_count": len(group),
                    "failure_category": category,
                    **details,
                }
            )
    records = pd.DataFrame(rows)
    report = {}
    for source, source_rows in records.groupby("source", sort=True):
        report[str(source)] = {}
        for method in methods:
            method_rows = source_rows.loc[source_rows["method"].eq(method)]
            counts = Counter(method_rows["failure_category"])
            report[str(source)][method] = {
                "queries": len(method_rows),
                "categories": {
                    category: {
                        "count": int(counts.get(category, 0)),
                        "rate": counts.get(category, 0) / len(method_rows),
                    }
                    for category in FAILURE_CATEGORIES
                },
                "by_phase_count": {
                    str(phase_count): {
                        "queries": len(stratum),
                        "complete_set_success_rate": float(
                            stratum["failure_category"]
                            .eq("complete_set_success")
                            .mean()
                        ),
                        "deep_omission_rate": float(
                            stratum["failure_category"].eq("deep_omission").mean()
                        ),
                    }
                    for phase_count, stratum in method_rows.groupby(
                        "phase_count",
                        sort=True,
                    )
                },
            }
    return report, records


def _confidence_scores(
    group: pd.DataFrame,
    method: str,
    budget: int,
) -> dict:
    ranked = _stable_rank(group, method)
    values = ranked[method].to_numpy(dtype=np.float64)
    if len(values) <= budget:
        boundary_margin = 1.0
    else:
        spread = float(values.max() - values.min())
        boundary_margin = (
            float(values[budget - 1] - values[budget]) / spread if spread > 0 else 1.0
        )
    if len(values) <= 1:
        top1_margin = 1.0
    else:
        spread = float(values.max() - values.min())
        top1_margin = float(values[0] - values[1]) / spread if spread > 0 else 1.0
    centered = values - values.mean()
    scale = centered.std()
    standardized = centered / scale if scale > 0 else np.zeros_like(values)
    exponentials = np.exp(standardized - standardized.max())
    probabilities = exponentials / exponentials.sum()
    return {
        "normalized_boundary_margin": boundary_margin,
        "normalized_top1_margin": top1_margin,
        "topk_softmax_mass": float(probabilities[:budget].sum()),
    }


def _bootstrap_risk_curve(
    records: pd.DataFrame,
    confidence_name: str,
    coverages: tuple[float, ...],
    repeats: int,
    seed: int,
) -> dict[str, dict[str, list[float] | None]]:
    clusters = sorted(records["cluster_id"].unique())
    cluster_indices = [
        np.flatnonzero(records["cluster_id"].to_numpy() == cluster)
        for cluster in clusters
    ]
    confidence = records[confidence_name].to_numpy(dtype=np.float64)
    success = records["success"].to_numpy(dtype=np.float64)
    phase_ap = records["phase_ap"].to_numpy(dtype=np.float64)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(clusters), size=(repeats, len(clusters)))
    samples = {
        str(coverage): {"success_rate": [], "phase_ap_macro": []}
        for coverage in coverages
    }
    for selected_clusters in sampled:
        indices = np.concatenate(
            [cluster_indices[index] for index in selected_clusters]
        )
        order = np.argsort(-confidence[indices], kind="stable")
        ranked = indices[order]
        for coverage in coverages:
            count = max(1, math.ceil(coverage * len(ranked)))
            chosen = ranked[:count]
            local_success = success[chosen]
            local_success = local_success[np.isfinite(local_success)]
            local_ap = phase_ap[chosen]
            local_ap = local_ap[np.isfinite(local_ap)]
            samples[str(coverage)]["success_rate"].append(
                float(local_success.mean()) if len(local_success) else np.nan
            )
            samples[str(coverage)]["phase_ap_macro"].append(
                float(local_ap.mean()) if len(local_ap) else np.nan
            )
    output = {}
    for coverage, endpoint_values in samples.items():
        output[coverage] = {}
        for endpoint, values in endpoint_values.items():
            finite = np.asarray(values)[np.isfinite(values)]
            output[coverage][endpoint] = (
                [
                    float(np.quantile(finite, 0.025)),
                    float(np.quantile(finite, 0.975)),
                ]
                if len(finite)
                else None
            )
    return output


def _risk_coverage(
    frame: pd.DataFrame,
    methods: tuple[str, ...],
    review_budget: int,
    coverages: tuple[float, ...],
    bootstrap_repeats: int,
    seed: int,
) -> tuple[dict, dict, pd.DataFrame]:
    rows = []
    for (source, query), group in frame.groupby(
        ["source", "query_id"],
        sort=True,
    ):
        for method in methods:
            values = _query_metrics(group, method, (review_budget,))
            rows.append(
                {
                    "source": source,
                    "query_id": query,
                    "cluster_id": group["cluster_id"].iloc[0],
                    "method": method,
                    "success": values[f"all_present_at_{review_budget}"],
                    "phase_ap": values["phase_ap"],
                    **_confidence_scores(group, method, review_budget),
                }
            )
    records = pd.DataFrame(rows)
    confidence_names = (
        "normalized_boundary_margin",
        "normalized_top1_margin",
        "topk_softmax_mass",
    )
    by_source = {}
    for source, source_rows in records.groupby("source", sort=True):
        by_source[str(source)] = {}
        for method in methods:
            method_rows = source_rows.loc[source_rows["method"].eq(method)].copy()
            by_source[str(source)][method] = {}
            for confidence_name in confidence_names:
                ordered = method_rows.sort_values(
                    [confidence_name, "query_id"],
                    ascending=[False, True],
                ).reset_index(drop=True)
                bootstrap = _bootstrap_risk_curve(
                    ordered,
                    confidence_name,
                    coverages,
                    bootstrap_repeats,
                    seed,
                )
                by_source[str(source)][method][confidence_name] = {}
                for coverage in coverages:
                    count = max(1, math.ceil(coverage * len(ordered)))
                    selected = ordered.head(count)
                    by_source[str(source)][method][confidence_name][str(coverage)] = {
                        "queries": count,
                        "clusters": int(selected["cluster_id"].nunique()),
                        "success_rate": float(selected["success"].mean()),
                        "risk": float(1 - selected["success"].mean()),
                        "phase_ap_macro": float(selected["phase_ap"].mean()),
                        "success_rate_ci95": bootstrap[str(coverage)]["success_rate"],
                        "phase_ap_macro_ci95": bootstrap[str(coverage)][
                            "phase_ap_macro"
                        ],
                    }
    source_macro = {}
    for method in methods:
        source_macro[method] = {}
        for confidence_name in confidence_names:
            source_macro[method][confidence_name] = {}
            for coverage in coverages:
                selected = [
                    by_source[source][method][confidence_name][str(coverage)]
                    for source in sorted(by_source)
                ]
                total_queries = sum(row["queries"] for row in selected)
                source_macro[method][confidence_name][str(coverage)] = {
                    "sources": len(selected),
                    "queries": total_queries,
                    "source_balanced_success": float(
                        np.mean([row["success_rate"] for row in selected])
                    ),
                    "query_weighted_success": float(
                        sum(row["success_rate"] * row["queries"] for row in selected)
                        / total_queries
                    ),
                }
    return by_source, source_macro, records


def run_diagnostics(
    frame: pd.DataFrame,
    methods: tuple[str, ...],
    sizes: tuple[int | None, ...] = DEFAULT_SIZES,
    budgets: tuple[int, ...] = DEFAULT_BUDGETS,
    review_budget: int = 3,
    coverages: tuple[float, ...] = DEFAULT_COVERAGES,
    bootstrap_repeats: int = 10_000,
    sampling_replicates: int = DEFAULT_SAMPLING_REPLICATES,
    seed: int = DEFAULT_SEED,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if not methods:
        raise ValueError("at least one method is required")
    if bootstrap_repeats < 1 or sampling_replicates < 1:
        raise ValueError("replicate counts must be positive")
    if review_budget < 1:
        raise ValueError("review_budget must be positive")
    if any(not 0 < coverage <= 1 for coverage in coverages):
        raise ValueError("coverages must be in (0, 1]")
    _validate(frame, methods)
    library_scaling, source_balanced = _library_scaling(
        frame,
        methods,
        sizes,
        budgets,
        sampling_replicates,
        bootstrap_repeats,
        seed,
    )
    failure_taxonomy, query_failures = _failure_taxonomy(
        frame,
        methods,
        review_budget,
    )
    risk_sources, risk_source_macro, query_risk = _risk_coverage(
        frame,
        methods,
        review_budget,
        coverages,
        bootstrap_repeats,
        seed,
    )
    report = {
        "status": "complete_set_diagnostics",
        "claim_boundary": (
            "Diagnostic analysis of frozen benchmark scores. Candidate-size "
            "curves are retrospective and are not prospective validation."
        ),
        "contract": {
            "methods": list(methods),
            "sizes": ["full" if size is None else size for size in sizes],
            "budgets": list(budgets),
            "review_budget": review_budget,
            "coverages": list(coverages),
            "bootstrap": "query-cluster with replacement",
            "bootstrap_repeats": bootstrap_repeats,
            "sampling_replicates": sampling_replicates,
            "seed": seed,
            "candidate_sampling": (
                "all positives retained; negatives sampled deterministically "
                "without replacement"
            ),
            "confidence_is_probability": False,
        },
        "library_scaling": library_scaling,
        "source_balanced_library_scaling": source_balanced,
        "failure_taxonomy": failure_taxonomy,
        "risk_coverage": {
            "sources": risk_sources,
            "source_macro": risk_source_macro,
        },
    }
    query_output = query_failures.merge(
        query_risk.drop(
            columns=["success", "phase_ap", "source"],
            errors="ignore",
        ),
        on=["query_id", "cluster_id", "method"],
        how="left",
        validate="one_to_one",
    )
    return report, query_output, query_risk
