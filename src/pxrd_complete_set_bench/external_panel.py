"""Six-method external comparison on the controlled AriadneX cohort."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

PANEL_SOURCE = "ariadnex_controlled"
QUERIES = tuple(f"sample_{index:02d}" for index in range(1, 26))
PHASES = ("A", "B", "C", "D")
BUDGETS = (1, 2, 3, 4)
DEFAULT_BOOTSTRAP = 10_000
DEFAULT_SEED = 20261123


def normalize_query_id(value: object) -> str:
    text = str(value).strip()
    if text.lower().startswith("sample "):
        number = int(text.split()[1])
        return f"sample_{number:02d}"
    if text.lower().startswith("sample_"):
        number = int(text.split("_", 1)[1])
        return f"sample_{number:02d}"
    raise ValueError(f"unexpected query identity: {value!r}")


def load_truth(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"source", "query_id", "cluster_id", "phase_id", "present"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"truth columns missing: {sorted(missing)}")
    truth = frame.loc[frame["source"].eq(PANEL_SOURCE)].copy()
    truth["query_id"] = truth["query_id"].map(normalize_query_id)
    if len(truth) != len(QUERIES) * len(PHASES):
        raise ValueError("controlled cohort must contain 25 queries x 4 candidates")
    if truth.duplicated(["query_id", "phase_id"]).any():
        raise ValueError("controlled cohort contains duplicate query-phase rows")
    if set(truth["query_id"]) != set(QUERIES):
        raise ValueError("controlled cohort query identities do not match")
    if set(truth["phase_id"]) != set(PHASES):
        raise ValueError("controlled cohort phase identities do not match")
    if not truth["present"].isin([0, 1]).all():
        raise ValueError("present labels must be binary")
    counts = truth.groupby("query_id")["present"].sum()
    if not counts.between(1, 3).all():
        raise ValueError("every query needs one to three present phases")
    if truth.groupby("query_id")["cluster_id"].nunique().ne(1).any():
        raise ValueError("each query must use exactly one cluster")
    return truth.sort_values(["query_id", "phase_id"]).reset_index(drop=True)


def load_predictions(path: Path, method_ids: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"method_id", "query_id", "phase_id", "score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"prediction columns missing: {sorted(missing)}")
    frame = frame[["method_id", "query_id", "phase_id", "score"]].copy()
    frame["query_id"] = frame["query_id"].map(normalize_query_id)
    frame["score"] = pd.to_numeric(frame["score"], errors="raise")
    if not np.isfinite(frame["score"]).all():
        raise ValueError("prediction scores must be finite")
    if set(frame["method_id"]) != set(method_ids):
        raise ValueError("prediction methods do not match the registry")
    if frame.duplicated(["method_id", "query_id", "phase_id"]).any():
        raise ValueError("duplicate method/query/phase prediction")
    expected = {
        (method, query, phase)
        for method in method_ids
        for query in QUERIES
        for phase in PHASES
    }
    observed = set(zip(frame["method_id"], frame["query_id"], frame["phase_id"]))
    if observed != expected:
        raise ValueError("prediction coverage is not methods x 25 queries x 4 phases")
    return frame.sort_values(["method_id", "query_id", "phase_id"]).reset_index(
        drop=True
    )


def load_registry(path: Path) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8"))
    methods = registry.get("methods")
    if not isinstance(methods, list) or not methods:
        raise ValueError("registry must contain a non-empty methods list")
    ids = tuple(method["id"] for method in methods)
    if len(ids) != len(set(ids)):
        raise ValueError("registry method identifiers must be unique")
    return registry


def _method_matrices(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    method: str,
) -> tuple[np.ndarray, np.ndarray]:
    query_index = {query: index for index, query in enumerate(QUERIES)}
    phase_index = {phase: index for index, phase in enumerate(PHASES)}
    labels = np.full((len(QUERIES), len(PHASES)), -1, dtype=np.int8)
    scores = np.full((len(QUERIES), len(PHASES)), np.nan, dtype=np.float64)
    for row in truth.itertuples(index=False):
        labels[query_index[row.query_id], phase_index[row.phase_id]] = int(row.present)
    local = predictions.loc[predictions["method_id"].eq(method)]
    for row in local.itertuples(index=False):
        scores[query_index[row.query_id], phase_index[row.phase_id]] = float(row.score)
    if (labels < 0).any() or not np.isfinite(scores).all():
        raise ValueError(f"incomplete panel matrices for {method}")
    return labels, scores


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    return float(average_precision_score(labels, scores))


def _query_average_precision(
    labels: np.ndarray,
    scores: np.ndarray,
) -> np.ndarray:
    return np.asarray(
        [
            _average_precision(labels[index], scores[index])
            for index in range(len(QUERIES))
        ],
        dtype=np.float64,
    )


def _rank_outcomes(
    labels: np.ndarray,
    scores: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    minimum_k = np.empty(len(QUERIES), dtype=np.int8)
    all_present = np.zeros((len(QUERIES), len(BUDGETS)), dtype=bool)
    for index in range(len(QUERIES)):
        order = np.argsort(-scores[index], kind="stable")
        positives = np.flatnonzero(labels[index])
        rank_by_phase = {phase: rank for rank, phase in enumerate(order, start=1)}
        minimum_k[index] = max(rank_by_phase[phase] for phase in positives)
        all_present[index] = [minimum_k[index] <= budget for budget in BUDGETS]
    return minimum_k, all_present


def _orders_with_ties(scores: np.ndarray) -> list[tuple[int, ...]]:
    groups: dict[float, list[int]] = {}
    for index, score in enumerate(scores):
        groups.setdefault(float(score), []).append(index)
    blocks = [
        list(itertools.permutations(groups[score]))
        for score in sorted(groups, reverse=True)
    ]
    return [
        tuple(index for block in order for index in block)
        for order in itertools.product(*blocks)
    ]


def _tie_order_bounds(
    labels: np.ndarray,
    scores: np.ndarray,
) -> dict:
    per_query = []
    for query_index in range(len(QUERIES)):
        orders = _orders_with_ties(scores[query_index])
        positives = set(np.flatnonzero(labels[query_index]).tolist())
        bounds = {}
        for budget in BUDGETS:
            outcomes = [positives.issubset(order[:budget]) for order in orders]
            bounds[str(budget)] = {
                "min": all(outcomes),
                "max": any(outcomes),
            }
        groups = {}
        for phase_index, score in enumerate(scores[query_index]):
            groups.setdefault(float(score), []).append(PHASES[phase_index])
        per_query.append(
            {
                "tie_groups": [phases for phases in groups.values() if len(phases) > 1],
                "legal_orders": len(orders),
                "all_present_bounds": bounds,
            }
        )
    return {
        "all_present": {
            str(budget): {
                "min": sum(
                    row["all_present_bounds"][str(budget)]["min"] for row in per_query
                )
                / len(QUERIES),
                "max": sum(
                    row["all_present_bounds"][str(budget)]["max"] for row in per_query
                )
                / len(QUERIES),
            }
            for budget in BUDGETS
        },
        "queries_with_ties": sum(bool(row["tie_groups"]) for row in per_query),
        "tie_groups": sum(len(row["tie_groups"]) for row in per_query),
        "per_query": {query: per_query[index] for index, query in enumerate(QUERIES)},
    }


def _metric_values(
    labels: np.ndarray,
    scores: np.ndarray,
) -> dict:
    query_ap = _query_average_precision(labels, scores)
    minimum_k, all_present = _rank_outcomes(labels, scores)
    values = {
        "phase_ap_micro": _average_precision(labels.ravel(), scores.ravel()),
        "phase_ap_macro": float(query_ap.mean()),
        "mean_minimum_k": float(minimum_k.mean()),
    }
    for index, budget in enumerate(BUDGETS):
        values[f"all_present_at_{budget}"] = float(all_present[:, index].mean())
    return values


def _percentile_interval(values: np.ndarray) -> list[float]:
    return [
        float(np.quantile(values, 0.025)),
        float(np.quantile(values, 0.975)),
    ]


def _bootstrap_samples(
    labels: dict[str, np.ndarray],
    scores: dict[str, np.ndarray],
    method_ids: tuple[str, ...],
    repeats: int,
    seed: int,
) -> dict[str, dict[str, np.ndarray]]:
    query_ap = {
        method: _query_average_precision(labels[method], scores[method])
        for method in method_ids
    }
    outcomes = {
        method: _rank_outcomes(labels[method], scores[method])[1]
        for method in method_ids
    }
    rng = np.random.default_rng(seed)
    sampled_queries = rng.integers(
        0,
        len(QUERIES),
        size=(repeats, len(QUERIES)),
    )
    endpoint_values = {
        method: {
            "phase_ap_micro": np.empty(repeats),
            "phase_ap_macro": np.empty(repeats),
            **{f"all_present_at_{budget}": np.empty(repeats) for budget in BUDGETS},
        }
        for method in method_ids
    }
    for repeat, selected in enumerate(sampled_queries):
        for method in method_ids:
            selected_labels = labels[method][selected].ravel()
            local_scores = scores[method][selected].ravel()
            endpoint_values[method]["phase_ap_micro"][repeat] = _average_precision(
                selected_labels, local_scores
            )
            endpoint_values[method]["phase_ap_macro"][repeat] = float(
                query_ap[method][selected].mean()
            )
            for budget_index, budget in enumerate(BUDGETS):
                endpoint_values[method][f"all_present_at_{budget}"][repeat] = float(
                    outcomes[method][selected, budget_index].mean()
                )
    return endpoint_values


def evaluate_external_panel(
    truth: pd.DataFrame,
    predictions: pd.DataFrame,
    registry: dict,
    repeats: int = DEFAULT_BOOTSTRAP,
    seed: int = DEFAULT_SEED,
) -> dict:
    if repeats < 1:
        raise ValueError("bootstrap repeats must be positive")
    methods = registry["methods"]
    method_ids = tuple(method["id"] for method in methods)
    matrix_data = {
        method: _method_matrices(truth, predictions, method) for method in method_ids
    }
    labels = {method: data[0] for method, data in matrix_data.items()}
    scores = {method: data[1] for method, data in matrix_data.items()}
    method_results = {}
    for method in method_ids:
        metadata = next(item for item in methods if item["id"] == method)
        method_results[method] = {
            "display_name": metadata["display_name"],
            "family": metadata["family"],
            "metrics": _metric_values(labels[method], scores[method]),
            "tie_order_bounds": _tie_order_bounds(
                labels[method],
                scores[method],
            ),
        }

    bootstrap = _bootstrap_samples(
        labels,
        scores,
        method_ids,
        repeats,
        seed,
    )
    endpoints = (
        "phase_ap_micro",
        "phase_ap_macro",
        "all_present_at_1",
        "all_present_at_2",
        "all_present_at_3",
        "all_present_at_4",
    )
    for method in method_ids:
        method_results[method]["bootstrap_ci95"] = {
            endpoint: _percentile_interval(bootstrap[method][endpoint])
            for endpoint in endpoints
        }

    comparisons = {}
    for left_index, left in enumerate(method_ids):
        for right in method_ids[left_index + 1 :]:
            comparisons[f"{left}_minus_{right}"] = {
                endpoint: {
                    "estimate": (
                        method_results[left]["metrics"][endpoint]
                        - method_results[right]["metrics"][endpoint]
                    ),
                    "ci95": _percentile_interval(
                        bootstrap[left][endpoint] - bootstrap[right][endpoint]
                    ),
                }
                for endpoint in endpoints
            }

    return {
        "status": "controlled_external_panel_evaluated",
        "source": PANEL_SOURCE,
        "claim_boundary": (
            "One retrospective 25-query measured-mixture panel. "
            "This supports method-coverage and ranking diagnostics, not "
            "prospective validation or universal state of the art."
        ),
        "contract": {
            "queries": len(QUERIES),
            "candidates": list(PHASES),
            "budgets": list(BUDGETS),
            "bootstrap": "query-level with replacement",
            "bootstrap_repeats": repeats,
            "seed": seed,
            "average_precision": ("equal-score rows form one threshold block"),
            "all_present_tie_break": "phase_id ascending",
        },
        "methods": method_results,
        "pairwise_paired_deltas": comparisons,
    }


def canonical_payload(report: dict) -> dict:
    """Remove file locations while retaining hashes and evaluation settings."""
    payload = json.loads(json.dumps(report))
    for value in payload.get("inputs", {}).values():
        if isinstance(value, dict):
            value.pop("file", None)
    return payload


def canonical_digest(report: dict) -> str:
    encoded = json.dumps(
        canonical_payload(report),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
