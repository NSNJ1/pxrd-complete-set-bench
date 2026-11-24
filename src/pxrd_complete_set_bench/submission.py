"""Score external candidate rankings with partial prediction coverage."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRUTH_COLUMNS = {"source", "query_id", "cluster_id", "phase_id", "present"}
PREDICTION_COLUMNS = {"method_id", "source", "query_id", "phase_id", "score"}


def validate_truth(frame: pd.DataFrame) -> pd.DataFrame:
    missing = TRUTH_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"truth columns missing: {sorted(missing)}")
    truth = frame[list(TRUTH_COLUMNS)].copy()
    if truth.isna().any().any():
        raise ValueError("truth identities and labels cannot be null")
    if truth.duplicated(["source", "query_id", "phase_id"]).any():
        raise ValueError("duplicate truth source/query/phase rows")
    if not truth["present"].isin([0, 1]).all():
        raise ValueError("truth labels must be binary")
    grouped = truth.groupby(["source", "query_id"], sort=False)
    if grouped["cluster_id"].nunique().ne(1).any():
        raise ValueError("each query must have exactly one cluster")
    if grouped["present"].sum().lt(1).any():
        raise ValueError("every query needs at least one positive phase")
    return truth.sort_values(["source", "query_id", "phase_id"]).reset_index(drop=True)


def validate_predictions(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    missing = PREDICTION_COLUMNS - set(predictions.columns)
    if missing:
        raise ValueError(f"prediction columns missing: {sorted(missing)}")
    local = predictions[list(PREDICTION_COLUMNS)].copy()
    if local[["method_id", "source", "query_id", "phase_id"]].isna().any().any():
        raise ValueError("prediction identities cannot be null")
    local["score"] = pd.to_numeric(local["score"], errors="raise")
    if not np.isfinite(local["score"]).all():
        raise ValueError("prediction scores must be finite")
    if local.duplicated(["method_id", "source", "query_id", "phase_id"]).any():
        raise ValueError("duplicate method/source/query/phase predictions")

    truth_keys = set(
        zip(truth["source"], truth["query_id"], truth["phase_id"], strict=True)
    )
    prediction_keys = set(
        zip(local["source"], local["query_id"], local["phase_id"], strict=True)
    )
    unknown = prediction_keys - truth_keys
    if unknown:
        example = min(unknown)
        raise ValueError(f"prediction contains an unknown candidate: {example}")
    return local.sort_values(
        ["method_id", "source", "query_id", "phase_id"]
    ).reset_index(drop=True)


def average_precision_with_missing(
    labels: np.ndarray,
    scores: np.ndarray,
    phase_ids: pd.Series,
    total_positive_count: int | None = None,
) -> float:
    """Compute AP over submitted candidates while keeping all positives in recall."""
    labels = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(scores, dtype=np.float64)
    positive_count = (
        int(labels.sum()) if total_positive_count is None else total_positive_count
    )
    if positive_count < int(labels.sum()):
        raise ValueError("total_positive_count cannot be smaller than submitted labels")
    if positive_count == 0:
        raise ValueError("average precision needs at least one positive")
    if len(labels) == 0:
        return 0.0

    ordered = sorted(
        range(len(labels)),
        key=lambda index: (-scores[index], str(phase_ids.iloc[index])),
    )
    average_precision = 0.0
    seen = 0
    true_positives = 0
    previous_recall = 0.0
    start = 0
    while start < len(ordered):
        stop = start + 1
        while stop < len(ordered) and scores[ordered[stop]] == scores[ordered[start]]:
            stop += 1
        block = ordered[start:stop]
        seen += len(block)
        true_positives += int(labels[block].sum())
        precision = true_positives / seen
        recall = true_positives / positive_count
        average_precision += (recall - previous_recall) * precision
        previous_recall = recall
        start = stop
    return float(average_precision)


def _query_metrics(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    budgets: tuple[int, ...],
) -> dict:
    merged = truth.merge(
        predictions,
        on=["source", "query_id", "phase_id"],
        how="left",
        validate="one_to_one",
    )
    submitted = merged.dropna(subset=["score"]).sort_values(
        ["score", "phase_id"],
        ascending=[False, True],
        kind="stable",
    )
    positive_count = int(merged["present"].sum())
    result = {
        "candidate_coverage": len(submitted) / len(merged),
        "positive_coverage": (
            int(submitted.loc[submitted["present"].eq(1), "score"].count())
            / positive_count
        ),
        "phase_ap": (
            average_precision_with_missing(
                submitted["present"].to_numpy(),
                submitted["score"].to_numpy(dtype=float),
                submitted["phase_id"],
                positive_count,
            )
            if len(submitted)
            else 0.0
        ),
    }
    present = submitted["present"].to_numpy(dtype=np.int8)
    for budget in budgets:
        result[f"all_present_at_{budget}"] = float(
            len(present) > 0 and int(present[:budget].sum()) == positive_count
        )
    return result


def _cluster_bootstrap(
    values: pd.DataFrame,
    column: str,
    repeats: int,
    seed: int,
) -> list[float]:
    groups = {
        cluster: group[column].to_numpy(dtype=float)
        for cluster, group in values.groupby("cluster_id", sort=True)
    }
    clusters = sorted(groups)
    rng = np.random.default_rng(seed)
    samples = np.empty(repeats)
    for repeat in range(repeats):
        selected = rng.choice(clusters, size=len(clusters), replace=True)
        samples[repeat] = np.concatenate(
            [groups[cluster] for cluster in selected]
        ).mean()
    return [
        float(np.quantile(samples, 0.025)),
        float(np.quantile(samples, 0.975)),
    ]


def score_submission(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    budgets: tuple[int, ...] = (1, 2, 3, 4, 5, 10),
    repeats: int = 10_000,
    seed: int = 20261124,
) -> dict:
    if not budgets or budgets[0] < 1:
        raise ValueError("budgets must be positive")
    if repeats < 1:
        raise ValueError("bootstrap repeats must be positive")
    truth = validate_truth(truth)
    predictions = validate_predictions(truth, predictions)
    query_count = truth.groupby(["source", "query_id"]).ngroups
    method_reports = {}

    for method_id, method_predictions in predictions.groupby("method_id", sort=True):
        source_reports = {}
        covered_queries = method_predictions.groupby(["source", "query_id"]).ngroups
        for source, source_truth in truth.groupby("source", sort=True):
            source_predictions = method_predictions.loc[
                method_predictions["source"].eq(source)
            ]
            records = []
            for (_, query_id), query_truth in source_truth.groupby(
                ["source", "query_id"],
                sort=True,
            ):
                query_predictions = source_predictions.loc[
                    source_predictions["query_id"].eq(query_id)
                ]
                metrics = _query_metrics(query_truth, query_predictions, budgets)
                records.append(
                    {
                        "query_id": query_id,
                        "cluster_id": query_truth["cluster_id"].iloc[0],
                        **metrics,
                    }
                )
            local = pd.DataFrame(records)
            endpoints = {
                "phase_ap_macro": float(local["phase_ap"].mean()),
                "candidate_coverage": float(local["candidate_coverage"].mean()),
                "positive_coverage": float(local["positive_coverage"].mean()),
            }
            covered = local.loc[local["candidate_coverage"].gt(0)]
            endpoints["covered_query_phase_ap_macro"] = (
                float(covered["phase_ap"].mean()) if len(covered) else None
            )
            for budget in budgets:
                key = f"all_present_at_{budget}"
                endpoints[key] = float(local[key].mean())
                endpoints[f"covered_query_{key}"] = (
                    float(covered[key].mean()) if len(covered) else None
                )
            intervals = {
                "phase_ap_macro": _cluster_bootstrap(
                    local,
                    "phase_ap",
                    repeats,
                    seed,
                ),
                "candidate_coverage": _cluster_bootstrap(
                    local,
                    "candidate_coverage",
                    repeats,
                    seed,
                ),
                "positive_coverage": _cluster_bootstrap(
                    local,
                    "positive_coverage",
                    repeats,
                    seed,
                ),
            }
            for budget in budgets:
                key = f"all_present_at_{budget}"
                intervals[key] = _cluster_bootstrap(
                    local,
                    key,
                    repeats,
                    seed,
                )
            source_reports[source] = {
                "queries": len(local),
                "clusters": int(local["cluster_id"].nunique()),
                "queries_with_predictions": int(
                    local["candidate_coverage"].gt(0).sum()
                ),
                "metrics": endpoints,
                "bootstrap_ci95": intervals,
            }
        method_reports[method_id] = {
            "query_coverage": covered_queries / query_count,
            "sources": source_reports,
        }

    return {
        "status": "partial_submission_scored",
        "claim_boundary": (
            "Missing candidate scores are treated as not submitted. They never "
            "enter a ranking, lower coverage, and make a query incomplete when a "
            "true phase is missing. Scores with different coverage are not pooled."
        ),
        "contract": {
            "budgets": list(budgets),
            "bootstrap": "source-specific cluster with replacement",
            "bootstrap_repeats": repeats,
            "seed": seed,
            "missing_candidate_policy": "not submitted; never ranked",
            "primary_denominator": "all truth queries, including uncovered queries",
            "conditional_endpoint_prefix": "covered_query_",
        },
        "methods": method_reports,
    }
