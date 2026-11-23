"""Audit label-permutation nulls, prior-only scores and detectable effects."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

SEED = 20261118
PERMUTATIONS = 2000
BUDGET = 3


def all_present(
    phases: list[str],
    scores: np.ndarray,
    positives: set[str],
    budget: int,
) -> bool:
    order = sorted(
        range(len(phases)),
        key=lambda index: (-scores[index], phases[index]),
    )
    return positives.issubset({phases[index] for index in order[:budget]})


def query_average_precision(
    labels: np.ndarray,
    scores: np.ndarray,
) -> float:
    return float(average_precision_score(labels, scores))


def cluster_mean(values: np.ndarray, clusters: np.ndarray) -> np.ndarray:
    frame = pd.DataFrame({"value": values, "cluster": clusters})
    return frame.groupby("cluster", sort=False)["value"].mean().to_numpy()


def minimum_detectable_difference(
    left: np.ndarray,
    right: np.ndarray,
    clusters: np.ndarray,
) -> dict:
    left_clusters = cluster_mean(left.astype(float), clusters)
    right_clusters = cluster_mean(right.astype(float), clusters)
    difference = left_clusters - right_clusters
    variance = float(difference.var(ddof=1))
    standard_error = math.sqrt(max(variance, 0.0) / len(difference))
    observed = float(difference.mean())
    mde = (1.959963984540054 + 0.8416212335729143) * standard_error
    required_clusters = None
    if abs(observed) > 0:
        required_clusters = math.ceil(
            ((1.959963984540054 + 0.8416212335729143) ** 2) * variance / (observed**2)
        )
    return {
        "observed_difference": observed,
        "cluster_variance": variance,
        "clusters": len(difference),
        "minimum_detectable_difference_80pct": float(mde),
        "clusters_for_observed_difference_80pct": required_clusters,
    }


def load_queries(group: pd.DataFrame) -> list[dict]:
    queries = []
    for query_id, local in group.groupby("query_id", sort=True):
        phases = sorted(local["phase_id"].astype(str))
        local = local.set_index("phase_id").loc[phases]
        positives = set(local.index[local["present"].eq(1)].astype(str))
        queries.append(
            {
                "query_id": query_id,
                "cluster_id": str(local["cluster_id"].iloc[0]),
                "phases": phases,
                "positives": positives,
                "labels": local["present"].to_numpy(dtype=np.int8),
                "baseline_score": local["baseline_score"].to_numpy(float),
                "method_score": local["method_score"].to_numpy(float),
            }
        )
    return queries


def frequency_prior_scores(queries: list[dict]) -> list[np.ndarray]:
    phase_counts = Counter()
    for query in queries:
        phase_counts.update(query["positives"])
    query_count = len(queries)
    prior_scores = []
    for query in queries:
        scores = []
        for phase in query["phases"]:
            count = phase_counts[phase] - int(phase in query["positives"])
            scores.append((count + 1.0) / (query_count - 1.0 + 2.0))
        prior_scores.append(np.asarray(scores))
    return prior_scores


def score_arrays(
    queries: list[dict],
    prior_scores: list[np.ndarray],
) -> dict[str, list[np.ndarray]]:
    return {
        "baseline_score": [query["baseline_score"] for query in queries],
        "method_score": [query["method_score"] for query in queries],
        "frequency_prior": prior_scores,
    }


def all_present_outcomes(
    queries: list[dict],
    scores: dict[str, list[np.ndarray]],
) -> dict[str, np.ndarray]:
    return {
        method: np.asarray(
            [
                all_present(
                    query["phases"],
                    local_scores,
                    query["positives"],
                    BUDGET,
                )
                for query, local_scores in zip(
                    queries,
                    method_scores,
                    strict=True,
                )
            ]
        )
        for method, method_scores in scores.items()
    }


def permutation_null(
    queries: list[dict],
    scores: dict[str, list[np.ndarray]],
    permutations: int,
    seed: int,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    null_rates = {method: np.empty(permutations) for method in scores}
    for repeat in range(permutations):
        permuted = []
        for query in queries:
            labels = query["labels"].copy()
            rng.shuffle(labels)
            positives = {
                phase
                for phase, label in zip(query["phases"], labels, strict=True)
                if label == 1
            }
            permuted.append(positives)
        for method, method_null in null_rates.items():
            values = []
            for query, phase_scores, positives in zip(
                queries,
                scores[method],
                permuted,
                strict=True,
            ):
                values.append(
                    all_present(
                        query["phases"],
                        phase_scores,
                        positives,
                        BUDGET,
                    )
                )
            method_null[repeat] = float(np.mean(values))
    return null_rates


def phase_ap(
    queries: list[dict],
    scores: dict[str, list[np.ndarray]],
) -> tuple[dict, dict[str, np.ndarray]]:
    method_ap = {}
    query_ap = {}
    for method, method_scores in scores.items():
        paired_qap = np.asarray(
            [
                query_average_precision(query["labels"], local_scores)
                for query, local_scores in zip(
                    queries,
                    method_scores,
                    strict=True,
                )
            ]
        )
        query_ap[method] = paired_qap
        method_ap[method] = {
            "micro": float(
                average_precision_score(
                    np.concatenate([query["labels"] for query in queries]),
                    np.concatenate(method_scores),
                )
            ),
            "macro": float(paired_qap.mean()),
        }
    return method_ap, query_ap


def power_comparisons(
    queries: list[dict],
    actual_success: dict[str, np.ndarray],
    query_ap: dict[str, np.ndarray],
) -> dict:
    clusters = np.asarray([query["cluster_id"] for query in queries])
    comparisons = {}
    for left, right in (
        ("method_score", "baseline_score"),
        ("method_score", "frequency_prior"),
        ("baseline_score", "frequency_prior"),
    ):
        comparisons[f"{left}_minus_{right}"] = {
            "all_present_at_3": minimum_detectable_difference(
                actual_success[left],
                actual_success[right],
                clusters,
            ),
            "query_ap": minimum_detectable_difference(
                query_ap[left],
                query_ap[right],
                clusters,
            ),
        }
    return comparisons


def summarize_nulls(
    null_rates: dict[str, np.ndarray],
    actual_success: dict[str, np.ndarray],
    permutations: int,
) -> dict:
    summary = {}
    for method, values in null_rates.items():
        actual = float(actual_success[method].mean())
        summary[method] = {
            "actual_all_present_at_3": actual,
            "null_mean": float(values.mean()),
            "null_ci95": [
                float(np.quantile(values, 0.025)),
                float(np.quantile(values, 0.975)),
            ],
            "empirical_one_sided_p": float(
                (1 + int(np.sum(values >= actual))) / (permutations + 1)
            ),
        }
    return summary


def audit_source(
    group: pd.DataFrame,
    permutations: int,
    seed: int,
) -> dict:
    sources = sorted(group["source"].unique())
    if len(sources) != 1:
        raise ValueError("audit_source expected one source")
    queries = load_queries(group)
    prior_scores = frequency_prior_scores(queries)
    scores = score_arrays(queries, prior_scores)
    actual_success = all_present_outcomes(queries, scores)
    null_rates = permutation_null(queries, scores, permutations, seed)
    method_ap, query_ap = phase_ap(queries, scores)
    comparisons = power_comparisons(queries, actual_success, query_ap)

    return {
        "queries": len(queries),
        "clusters": int(group["cluster_id"].nunique()),
        "phases": len(group["phase_id"].unique()),
        "all_present_at_3": {
            method: float(values.mean()) for method, values in actual_success.items()
        },
        "phase_ap": method_ap,
        "label_permutation": summarize_nulls(
            null_rates,
            actual_success,
            permutations,
        ),
        "power": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    table = pd.read_csv(args.table)
    results = {}
    for index, (source, group) in enumerate(table.groupby("source", sort=True)):
        results[source] = audit_source(
            group.copy(),
            args.permutations,
            args.seed + index,
        )
    report = {
        "status": "null_and_power_audit",
        "claim_boundary": (
            "Within-query label permutations preserve the number of true "
            "phases but destroy phase identity. Power values are design "
            "diagnostics, not post-hoc proof that an observed effect is real."
        ),
        "contract": {
            "review_budget": BUDGET,
            "permutations": args.permutations,
            "seed": args.seed,
            "cluster_unit": "cluster_id",
        },
        "sources": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                source: {
                    "all_present_at_3": values["all_present_at_3"],
                    "permutation_p": {
                        method: null["empirical_one_sided_p"]
                        for method, null in values["label_permutation"].items()
                    },
                }
                for source, values in results.items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
