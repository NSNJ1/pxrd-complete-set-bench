"""Measure whether method rankings survive changes in benchmark endpoint."""

from __future__ import annotations

import itertools
from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

ENDPOINT_DIRECTIONS = {
    "phase_ap_micro": True,
    "phase_ap_macro": True,
    "all_present_at_2": True,
    "all_present_at_3": True,
    "tie_min_all_present_at_3": True,
    "tie_max_all_present_at_3": True,
    "mean_minimum_k": False,
}


def _orders_with_ties(scores: np.ndarray) -> list[tuple[int, ...]]:
    groups: dict[float, list[int]] = {}
    for index, score in enumerate(scores):
        groups.setdefault(float(score), []).append(index)
    blocks = [
        list(itertools.permutations(groups[score]))
        for score in sorted(groups, reverse=True)
    ]
    order_count = int(np.prod([len(block) for block in blocks], dtype=np.int64))
    if order_count > 10_000:
        raise ValueError("tie groups produce too many legal orders")
    return [
        tuple(index for block in order for index in block)
        for order in itertools.product(*blocks)
    ]


def _query_endpoints(
    frame: pd.DataFrame,
    methods: Iterable[str],
    budgets: tuple[int, ...],
) -> dict:
    methods = tuple(methods)
    missing = {"query_id", "phase_id", "present", *methods} - set(frame.columns)
    if missing:
        raise ValueError(f"scores columns missing: {sorted(missing)}")

    records = []
    for query_id, group in frame.groupby("query_id", sort=True):
        group = group.sort_values("phase_id", kind="stable")
        labels = group["present"].to_numpy(dtype=np.int8)
        if not np.isin(labels, [0, 1]).all():
            raise ValueError("present labels must be binary")
        if not labels.any() or labels.all():
            raise ValueError("each query needs at least one positive and one negative")

        method_values = {}
        method_rows = {}
        for method in methods:
            scores = group[method].to_numpy(dtype=np.float64)
            if not np.isfinite(scores).all():
                raise ValueError("scores must be finite")
            fixed_order = sorted(
                range(len(group)),
                key=lambda index: (-scores[index], group.iloc[index]["phase_id"]),
            )
            positive_ranks = [
                rank
                for rank, index in enumerate(fixed_order, start=1)
                if labels[index] == 1
            ]
            positive_count = len(positive_ranks)
            minimum_k = max(positive_ranks)
            legal_orders = _orders_with_ties(scores)
            positives = set(np.flatnonzero(labels).tolist())
            values = {
                "query_ap": float(average_precision_score(labels, scores)),
                "mean_minimum_k": float(minimum_k),
            }
            for budget in budgets:
                values[f"all_present_at_{budget}"] = float(
                    int(labels[fixed_order[:budget]].sum()) == positive_count
                )
                if budget == 3:
                    outcomes = [
                        positives.issubset(set(order[:budget]))
                        for order in legal_orders
                    ]
                    values["tie_min_all_present_at_3"] = float(all(outcomes))
                    values["tie_max_all_present_at_3"] = float(any(outcomes))
            method_values[method] = values
            method_rows[method] = (labels.copy(), scores.copy())
        records.append(
            {
                "query_id": query_id,
                "values": method_values,
                "rows": method_rows,
            }
        )
    return {"records": records, "methods": methods, "budgets": budgets}


def endpoint_values(
    panel: dict,
    selected: np.ndarray,
) -> dict[str, dict[str, float]]:
    selected = np.asarray(selected, dtype=np.int64)
    records = panel["records"]
    result = {}
    for method in panel["methods"]:
        labels = np.concatenate(
            [records[index]["rows"][method][0] for index in selected]
        )
        scores = np.concatenate(
            [records[index]["rows"][method][1] for index in selected]
        )
        method_result = {
            "phase_ap_micro": float(average_precision_score(labels, scores)),
            "phase_ap_macro": float(
                np.mean(
                    [records[index]["values"][method]["query_ap"] for index in selected]
                )
            ),
            "mean_minimum_k": float(
                np.mean(
                    [
                        records[index]["values"][method]["mean_minimum_k"]
                        for index in selected
                    ]
                )
            ),
        }
        for budget in panel["budgets"]:
            method_result[f"all_present_at_{budget}"] = float(
                np.mean(
                    [
                        records[index]["values"][method][f"all_present_at_{budget}"]
                        for index in selected
                    ]
                )
            )
        method_result["tie_min_all_present_at_3"] = float(
            np.mean(
                [
                    records[index]["values"][method]["tie_min_all_present_at_3"]
                    for index in selected
                ]
            )
        )
        method_result["tie_max_all_present_at_3"] = float(
            np.mean(
                [
                    records[index]["values"][method]["tie_max_all_present_at_3"]
                    for index in selected
                ]
            )
        )
        result[method] = method_result
    return result


def _average_ranks(values: np.ndarray, higher_is_better: bool) -> np.ndarray:
    oriented = values if higher_is_better else -values
    order = np.argsort(-oriented, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and np.isclose(
            oriented[order[stop]],
            oriented[order[start]],
            rtol=0.0,
            atol=1e-15,
        ):
            stop += 1
        average_rank = (start + 1 + stop) / 2
        ranks[order[start:stop]] = average_rank
        start = stop
    return ranks


def endpoint_ranks(
    values: dict[str, dict[str, float]],
    methods: tuple[str, ...],
) -> dict[str, np.ndarray]:
    return {
        endpoint: _average_ranks(
            np.asarray([values[method][endpoint] for method in methods]),
            higher_is_better,
        )
        for endpoint, higher_is_better in ENDPOINT_DIRECTIONS.items()
    }


def _pairwise_reversal_fraction(
    left_values: np.ndarray,
    right_values: np.ndarray,
    left_higher: bool,
    right_higher: bool,
) -> tuple[float | None, int]:
    comparable = 0
    reversals = 0
    for left_index in range(len(left_values)):
        for right_index in range(left_index + 1, len(left_values)):
            left_delta = left_values[left_index] - left_values[right_index]
            right_delta = right_values[left_index] - right_values[right_index]
            if not left_higher:
                left_delta = -left_delta
            if not right_higher:
                right_delta = -right_delta
            if np.isclose(left_delta, 0.0, atol=1e-15) or np.isclose(
                right_delta,
                0.0,
                atol=1e-15,
            ):
                continue
            comparable += 1
            reversals += int(np.sign(left_delta) != np.sign(right_delta))
    fraction = reversals / comparable if comparable else None
    return fraction, comparable


def rank_reversal_report(
    frame: pd.DataFrame,
    methods: tuple[str, ...],
    budgets: tuple[int, ...] = (1, 2, 3, 4),
    repeats: int = 10_000,
    seed: int = 20261123,
) -> dict:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if not {2, 3}.issubset(budgets):
        raise ValueError("rank-reversal endpoints require budgets 2 and 3")
    panel = _query_endpoints(frame, methods, budgets)
    count = len(panel["records"])
    observed_values = endpoint_values(panel, np.arange(count))
    observed_ranks = endpoint_ranks(observed_values, methods)

    rng = np.random.default_rng(seed)
    selected = rng.integers(0, count, size=(repeats, count))
    bootstrap_values = {
        method: {endpoint: np.empty(repeats) for endpoint in ENDPOINT_DIRECTIONS}
        for method in methods
    }
    bootstrap_ranks = {
        endpoint: np.empty((repeats, len(methods)), dtype=np.float64)
        for endpoint in ENDPOINT_DIRECTIONS
    }
    for repeat, selected_queries in enumerate(selected):
        values = endpoint_values(panel, selected_queries)
        for method in methods:
            for endpoint in ENDPOINT_DIRECTIONS:
                bootstrap_values[method][endpoint][repeat] = values[method][endpoint]
        ranks = endpoint_ranks(values, methods)
        for endpoint in ENDPOINT_DIRECTIONS:
            bootstrap_ranks[endpoint][repeat] = ranks[endpoint]

    endpoint_pairs = {}
    all_pair_fractions = []
    all_bootstrap_fractions = []
    endpoint_names = tuple(ENDPOINT_DIRECTIONS)
    for left_index, left in enumerate(endpoint_names):
        for right in endpoint_names[left_index + 1 :]:
            observed, comparable = _pairwise_reversal_fraction(
                np.asarray([observed_values[method][left] for method in methods]),
                np.asarray([observed_values[method][right] for method in methods]),
                ENDPOINT_DIRECTIONS[left],
                ENDPOINT_DIRECTIONS[right],
            )
            resampled = []
            for repeat in range(repeats):
                fraction, _ = _pairwise_reversal_fraction(
                    np.asarray(
                        [bootstrap_values[method][left][repeat] for method in methods]
                    ),
                    np.asarray(
                        [bootstrap_values[method][right][repeat] for method in methods]
                    ),
                    ENDPOINT_DIRECTIONS[left],
                    ENDPOINT_DIRECTIONS[right],
                )
                if fraction is not None:
                    resampled.append(fraction)
            empirical = float(np.mean(resampled)) if resampled else None
            interval = (
                [
                    float(np.quantile(resampled, 0.025)),
                    float(np.quantile(resampled, 0.975)),
                ]
                if resampled
                else None
            )
            endpoint_pairs[f"{left}__{right}"] = {
                "observed_pairwise_reversal_fraction": observed,
                "comparable_method_pairs": comparable,
                "bootstrap_mean_reversal_fraction": empirical,
                "bootstrap_ci95": interval,
            }
            if observed is not None:
                all_pair_fractions.append(observed)
            if empirical is not None:
                all_bootstrap_fractions.append(empirical)

    rank_stability = {}
    for endpoint in endpoint_names:
        rank_stability[endpoint] = {}
        for method_index, method in enumerate(methods):
            samples = bootstrap_ranks[endpoint][:, method_index]
            rank_stability[endpoint][method] = {
                "observed_rank": float(observed_ranks[endpoint][method_index]),
                "same_rank_fraction": float(
                    np.mean(np.isclose(samples, observed_ranks[endpoint][method_index]))
                ),
                "rank_ci95": [
                    float(np.quantile(samples, 0.025)),
                    float(np.quantile(samples, 0.975)),
                ],
            }

    headline_key = "phase_ap_micro__all_present_at_3"
    return {
        "status": "endpoint_rank_reversal_audit",
        "claim_boundary": (
            "Exploratory endpoint sensitivity on one 25-query retrospective panel. "
            "Reversal fractions describe benchmark-metric dependence, not a new "
            "significance test for state-of-the-art performance."
        ),
        "contract": {
            "queries": count,
            "methods": len(methods),
            "bootstrap": "query-level with replacement",
            "bootstrap_repeats": repeats,
            "seed": seed,
            "endpoints": {
                endpoint: ("larger_is_better" if direction else "smaller_is_better")
                for endpoint, direction in ENDPOINT_DIRECTIONS.items()
            },
        },
        "observed": {
            endpoint: {
                method: {
                    "value": observed_values[method][endpoint],
                    "rank": float(observed_ranks[endpoint][index]),
                }
                for index, method in enumerate(methods)
            }
            for endpoint in endpoint_names
        },
        "endpoint_pairwise_reversals": endpoint_pairs,
        "aggregate_pairwise_reversal_fraction": (
            float(np.mean(all_pair_fractions)) if all_pair_fractions else None
        ),
        "bootstrap_aggregate_pairwise_reversal_fraction": (
            float(np.mean(all_bootstrap_fractions)) if all_bootstrap_fractions else None
        ),
        "headline": endpoint_pairs[headline_key],
        "rank_stability": rank_stability,
    }
