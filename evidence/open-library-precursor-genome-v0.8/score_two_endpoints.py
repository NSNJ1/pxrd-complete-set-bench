#!/usr/bin/env python3
"""Score candidate-ranking and unknown-evidence endpoints for a frozen source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def ranked_ids(ids: list[str], scores: dict[str, float]) -> list[str]:
    return sorted(ids, key=lambda phase_id: (-float(scores[phase_id]), phase_id))


def full_score_lookup(
    candidate_table: pd.DataFrame,
    cases: pd.DataFrame,
) -> tuple[dict[tuple[str, str], float], dict[str, dict[str, float]]]:
    closed = cases[cases["condition"].eq("closed")]
    closed_case_to_query = dict(zip(closed["case_id"], closed["query_id"], strict=True))
    candidate_table = candidate_table[
        candidate_table["case_id"].isin(closed_case_to_query)
    ]
    lookup = {}
    by_query: dict[str, dict[str, float]] = {}
    for row in candidate_table.itertuples(index=False):
        query_id = closed_case_to_query[row.case_id]
        lookup[(query_id, row.phase_id)] = float(row.score)
        by_query.setdefault(query_id, {})[row.phase_id] = float(row.score)
    return lookup, by_query


def unavailable_percentile(
    omitted: str,
    scores: dict[str, float],
) -> float:
    omitted_score = float(scores[omitted])
    others = [float(value) for phase_id, value in scores.items() if phase_id != omitted]
    denominator = len(others)
    if denominator == 0:
        return 0.0
    return sum(value <= omitted_score for value in others) / denominator


def oof_flags(
    frame: pd.DataFrame,
    score_column: str,
    target: float,
) -> pd.Series:
    flags = pd.Series(False, index=frame.index)
    for cluster_id, cluster_frame in frame.groupby("cluster_id", sort=False):
        other_negatives = frame.loc[
            ~frame["cluster_id"].eq(cluster_id)
            & ~pd.to_numeric(frame["unknown_present"]).astype(bool),
            score_column,
        ]
        if other_negatives.empty:
            raise ValueError(f"no outside-cluster negatives for {cluster_id}")
        threshold = float(
            np.quantile(other_negatives.to_numpy(), 1.0 - target, method="higher")
        )
        flags.loc[cluster_frame.index] = (
            cluster_frame[score_column].astype(float) > threshold
        )
    return flags


def binary_metrics(
    frame: pd.DataFrame,
    score_column: str,
    flag_column: str,
    negative_condition: str | None = None,
) -> dict:
    if negative_condition is None:
        selected = frame.copy()
    else:
        selected = frame[
            pd.to_numeric(frame["unknown_present"]).astype(bool)
            | frame["condition"].eq(negative_condition)
        ].copy()
    labels = pd.to_numeric(selected["unknown_present"]).astype(int).to_numpy()
    scores = selected[score_column].astype(float).to_numpy()
    result = {
        "cases": len(selected),
        "positives": int(labels.sum()),
        "negatives": int((1 - labels).sum()),
        "auroc": float(roc_auc_score(labels, scores)),
        "average_precision": float(average_precision_score(labels, scores)),
    }
    for target in (0.05, 0.10):
        flags = selected[flag_column].astype(bool).to_numpy()
        result[f"far_{int(target * 100):02d}"] = {
            "negative_false_alarm_rate": float(flags[labels == 0].mean()),
            "unknown_detection_rate": float(flags[labels == 1].mean()),
            "silent_completion_rate": float(1.0 - flags[labels == 1].mean()),
        }
    return result


def ranking_metrics(
    cases: pd.DataFrame,
    truth: pd.DataFrame,
    actual: pd.DataFrame,
    fixed: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    actual_lookup = dict(
        zip(
            zip(actual["case_id"], actual["phase_id"], strict=True),
            actual["score"].astype(float),
            strict=True,
        )
    )
    fixed_lookup = dict(
        zip(
            zip(fixed["case_id"], fixed["phase_id"], strict=True),
            fixed["score"].astype(float),
            strict=True,
        )
    )
    truth_by_case = {
        case_id: frame
        for case_id, frame in truth.groupby("case_id", sort=False)
    }
    records = []
    for case in cases.itertuples(index=False):
        if case.condition == "closed":
            continue
        case_truth = truth_by_case[case.case_id]
        available = case_truth["phase_id"].tolist()
        actual_scores = {
            phase_id: actual_lookup[(case.case_id, phase_id)]
            for phase_id in available
        }
        fixed_scores = {
            phase_id: fixed_lookup[(case.case_id, phase_id)]
            for phase_id in available
        }
        actual_order = ranked_ids(available, actual_scores)
        fixed_order = ranked_ids(available, fixed_scores)
        actual_rank = {
            phase_id: rank for rank, phase_id in enumerate(actual_order, start=1)
        }
        fixed_rank = {
            phase_id: rank for rank, phase_id in enumerate(fixed_order, start=1)
        }
        retained_true = (
            case_truth.loc[case_truth["present"].eq(1), "phase_id"].tolist()
        )
        true_actual_order = [
            phase_id for phase_id in actual_order if phase_id in set(retained_true)
        ]
        true_fixed_order = [
            phase_id for phase_id in fixed_order if phase_id in set(retained_true)
        ]
        pair_reversal = False
        if len(retained_true) >= 2:
            for left_index, left in enumerate(retained_true):
                for right in retained_true[left_index + 1 :]:
                    pair_reversal |= (
                        fixed_rank[left] < fixed_rank[right]
                    ) != (
                        actual_rank[left] < actual_rank[right]
                    )
        actual_vector = np.array(
            [actual_scores[phase_id] for phase_id in available],
            dtype=float,
        )
        fixed_vector = np.array(
            [fixed_scores[phase_id] for phase_id in available],
            dtype=float,
        )
        actual_top1 = actual_order[0]
        fixed_top1 = fixed_order[0]
        actual_top3 = set(actual_order[:3])
        fixed_top3 = set(fixed_order[:3])
        records.append(
            {
                "case_id": case.case_id,
                "query_id": case.query_id,
                "cluster_id": case.cluster_id,
                "condition": case.condition,
                "omitted_phase_id": case.omitted_phase_id,
                "retained_true_count": len(retained_true),
                "order_changed": actual_order != fixed_order,
                "true_order_changed": true_actual_order != true_fixed_order,
                "true_pair_reversal": pair_reversal,
                "top1_changed": actual_top1 != fixed_top1,
                "top3_set_changed": actual_top3 != fixed_top3,
                "spearman": (
                    float(spearmanr(actual_vector, fixed_vector).statistic)
                    if len(available) > 1
                    else 1.0
                ),
                "kendall_tau": (
                    float(kendalltau(actual_vector, fixed_vector).statistic)
                    if len(available) > 1
                    else 1.0
                ),
                "max_abs_score_difference": float(
                    np.max(np.abs(actual_vector - fixed_vector))
                ),
                "scores_exactly_equal": bool(
                    np.array_equal(actual_vector, fixed_vector)
                ),
            }
        )
    frame = pd.DataFrame(records)
    true_omissions = frame["condition"].eq("omit_present")
    eligible_true_order = true_omissions & frame["retained_true_count"].ge(2)
    all_omissions_eligible = frame["retained_true_count"].ge(2)
    by_condition = {}
    for condition, group in frame.groupby("condition", sort=False):
        eligible = group["retained_true_count"] >= 2
        by_condition[condition] = {
            "cases": len(group),
            "candidate_order_changed": int(group["order_changed"].sum()),
            "true_subset_order_eligible_cases": int(eligible.sum()),
            "true_subset_order_changed": int(
                group.loc[eligible, "true_order_changed"].sum()
            ),
        }
    summary = {
        "omission_cases": len(frame),
        "all_candidate_order_changed": int(frame["order_changed"].sum()),
        "all_candidate_order_change_rate": float(frame["order_changed"].mean()),
        "true_omission_cases": int(true_omissions.sum()),
        "true_omission_order_changed": int(
            frame.loc[true_omissions, "order_changed"].sum()
        ),
        "true_subset_order_changed": int(
            frame.loc[eligible_true_order, "true_order_changed"].sum()
        ),
        "true_subset_order_eligible_cases": int(eligible_true_order.sum()),
        "true_subset_order_change_rate": (
            float(frame.loc[eligible_true_order, "true_order_changed"].mean())
            if eligible_true_order.any()
            else None
        ),
        "all_omission_true_subset_order_changed": int(
            frame.loc[all_omissions_eligible, "true_order_changed"].sum()
        ),
        "all_omission_true_subset_order_eligible_cases": int(
            all_omissions_eligible.sum()
        ),
        "true_pair_reversal_cases": int(
            frame.loc[eligible_true_order, "true_pair_reversal"].sum()
        ),
        "by_condition": by_condition,
        "median_spearman": float(frame["spearman"].median()),
        "minimum_spearman": float(frame["spearman"].min()),
        "max_abs_score_difference": float(
            frame["max_abs_score_difference"].max()
        ),
    }
    return frame, summary


def retrieval_metrics(
    cases: pd.DataFrame,
    truth: pd.DataFrame,
    candidate_table: pd.DataFrame,
    label: str,
) -> dict:
    score_lookup = dict(
        zip(
            zip(
                candidate_table["case_id"],
                candidate_table["phase_id"],
                strict=True,
            ),
            candidate_table["score"].astype(float),
            strict=True,
        )
    )
    truth_by_case = {
        case_id: frame
        for case_id, frame in truth.groupby("case_id", sort=False)
    }
    budgets = (1, 2, 3, 5, 10, 20)
    rows = []
    for case in cases.itertuples(index=False):
        case_truth = truth_by_case[case.case_id]
        available = case_truth["phase_id"].tolist()
        scores = {
            phase_id: score_lookup[(case.case_id, phase_id)]
            for phase_id in available
        }
        order = ranked_ids(available, scores)
        present = set(
            case_truth.loc[case_truth["present"].eq(1), "phase_id"].tolist()
        )
        row = {
            "case_id": case.case_id,
            "condition": case.condition,
            "unknown_present": int(case.unknown_present),
            "true_count": len(present),
        }
        for budget in budgets:
            selected = set(order[:budget])
            if present:
                row[f"recall_at_{budget}"] = (
                    len(selected & present) / len(present)
                )
                row[f"all_present_at_{budget}"] = int(
                    present.issubset(selected)
                )
            else:
                row[f"recall_at_{budget}"] = np.nan
                row[f"all_present_at_{budget}"] = np.nan
        rows.append(row)
    frame = pd.DataFrame(rows)
    labels = truth["present"].astype(int).to_numpy()
    scores = np.array(
        [
            score_lookup[(row.case_id, row.phase_id)]
            for row in truth.itertuples(index=False)
        ]
    )
    summary = {
        "label": label,
        "candidate_level_auroc": float(roc_auc_score(labels, scores)),
        "candidate_level_average_precision": float(
            average_precision_score(labels, scores)
        ),
        "by_condition": {},
    }
    for condition, group in frame.groupby("condition"):
        summary["by_condition"][condition] = {
            "retrieval_eligible_cases": int(
                group["true_count"].gt(0).sum()
            ),
        } | {
            f"mean_recall_at_{budget}": float(
                group[f"recall_at_{budget}"].mean()
            )
            for budget in budgets
        } | {
            f"all_present_at_{budget}": float(
                group[f"all_present_at_{budget}"].mean()
            )
            for budget in budgets
        }
    return summary


def bootstrap(
    frame: pd.DataFrame,
    rank_frame: pd.DataFrame,
    repeats: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    clusters = sorted(frame["cluster_id"].unique())
    index_by_cluster = {
        cluster_id: frame.index[frame["cluster_id"].eq(cluster_id)].to_numpy()
        for cluster_id in clusters
    }
    rank_index_by_cluster = {
        cluster_id: rank_frame.index[
            rank_frame["cluster_id"].eq(cluster_id)
        ].to_numpy()
        for cluster_id in clusters
    }
    values = {
        "actual_auroc": [],
        "fixed_auroc": [],
        "percentile_auroc": [],
        "actual_minus_fixed": [],
        "actual_minus_percentile": [],
        "all_candidate_order_change_rate": [],
        "true_subset_order_change_rate": [],
    }
    for _ in range(repeats):
        sampled = rng.choice(clusters, size=len(clusters), replace=True)
        indices = np.concatenate([index_by_cluster[item] for item in sampled])
        rank_indices = np.concatenate(
            [rank_index_by_cluster[item] for item in sampled]
        )
        sample = frame.loc[indices]
        labels = pd.to_numeric(sample["unknown_present"]).astype(int).to_numpy()
        if len(np.unique(labels)) < 2:
            continue
        actual = float(roc_auc_score(labels, sample["actual_unknown_score"]))
        fixed = float(roc_auc_score(labels, sample["fixed_unknown_score"]))
        percentile = float(
            roc_auc_score(labels, sample["unavailable_percentile_score"])
        )
        rank_sample = rank_frame.loc[rank_indices]
        eligible = rank_sample["condition"].eq("omit_present") & rank_sample[
            "retained_true_count"
        ].ge(2)
        values["actual_auroc"].append(actual)
        values["fixed_auroc"].append(fixed)
        values["percentile_auroc"].append(percentile)
        values["actual_minus_fixed"].append(actual - fixed)
        values["actual_minus_percentile"].append(actual - percentile)
        values["all_candidate_order_change_rate"].append(
            float(rank_sample["order_changed"].mean())
        )
        if eligible.any():
            values["true_subset_order_change_rate"].append(
                float(rank_sample.loc[eligible, "true_order_changed"].mean())
            )
    intervals = {}
    for name, samples in values.items():
        array = np.asarray(samples, dtype=float)
        array = array[np.isfinite(array)]
        if array.size == 0:
            intervals[name] = {
                "median": None,
                "ci95": [None, None],
                "finite_replicates": 0,
                "status": "not_estimable",
            }
            continue
        intervals[name] = {
            "median": float(np.median(array)),
            "ci95": [
                float(np.quantile(array, 0.025)),
                float(np.quantile(array, 0.975)),
            ],
            "finite_replicates": len(array),
        }
    return {
        "repeats_requested": repeats,
        "seed": seed,
        "clusters": len(clusters),
        "intervals": intervals,
    }


def score_method(
    method_id: str,
    run_dir: Path,
    cases: pd.DataFrame,
    truth: pd.DataFrame,
    repeats: int,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    source_ids = sorted(cases["source"].astype(str).unique())
    if len(source_ids) != 1:
        raise ValueError(f"expected one source, found {source_ids}")
    source_id = source_ids[0]
    actual_candidates = pd.read_csv(run_dir / "candidate_predictions.csv")
    actual_cases = pd.read_csv(run_dir / "case_scores.csv")
    fixed_candidates = pd.read_csv(
        run_dir / "fixed_output_candidate_predictions.csv"
    )
    fixed_cases = pd.read_csv(run_dir / "fixed_output_case_scores.csv")

    full_lookup, full_by_query = full_score_lookup(fixed_candidates, cases)
    del full_lookup
    case_frame = cases.merge(
        actual_cases,
        on="case_id",
        validate="one_to_one",
    ).merge(
        fixed_cases.rename(columns={"unknown_score": "fixed_unknown_score"}),
        on="case_id",
        validate="one_to_one",
    )
    case_frame = case_frame.rename(
        columns={"unknown_score": "actual_unknown_score"}
    )
    percentile_scores = []
    for row in case_frame.itertuples(index=False):
        if row.condition == "closed":
            percentile_scores.append(0.0)
        else:
            percentile_scores.append(
                unavailable_percentile(
                    row.omitted_phase_id,
                    full_by_query[row.query_id],
                )
            )
    case_frame["unavailable_percentile_score"] = percentile_scores
    for score_column, stem in (
        ("actual_unknown_score", "actual"),
        ("fixed_unknown_score", "fixed"),
        ("unavailable_percentile_score", "percentile"),
    ):
        case_frame[f"{stem}_flag_far05"] = oof_flags(
            case_frame,
            score_column,
            0.05,
        )
        case_frame[f"{stem}_flag_far10"] = oof_flags(
            case_frame,
            score_column,
            0.10,
        )

    rank_frame, ranking_summary = ranking_metrics(
        cases,
        truth,
        actual_candidates,
        fixed_candidates,
    )
    retrieval_context = {
        "actual": retrieval_metrics(
            cases,
            truth,
            actual_candidates,
            "actual",
        ),
        "fixed_full_output": retrieval_metrics(
            cases,
            truth,
            fixed_candidates,
            "fixed_full_output",
        ),
    }
    unknown_summary = {
        "actual": {
            "all": binary_metrics(
                case_frame,
                "actual_unknown_score",
                "actual_flag_far05",
            ),
            "far05": binary_metrics(
                case_frame,
                "actual_unknown_score",
                "actual_flag_far05",
            )["far_05"],
            "far10": binary_metrics(
                case_frame,
                "actual_unknown_score",
                "actual_flag_far10",
            )["far_10"],
            "against_closed": binary_metrics(
                case_frame,
                "actual_unknown_score",
                "actual_flag_far05",
                "closed",
            ),
            "against_absent_omission": binary_metrics(
                case_frame,
                "actual_unknown_score",
                "actual_flag_far05",
                "omit_absent",
            ),
        },
        "fixed_full_residual": {
            "all": binary_metrics(
                case_frame,
                "fixed_unknown_score",
                "fixed_flag_far05",
            ),
            "far05": binary_metrics(
                case_frame,
                "fixed_unknown_score",
                "fixed_flag_far05",
            )["far_05"],
            "far10": binary_metrics(
                case_frame,
                "fixed_unknown_score",
                "fixed_flag_far10",
            )["far_10"],
        },
        "unavailable_omitted_percentile": {
            "all": binary_metrics(
                case_frame,
                "unavailable_percentile_score",
                "percentile_flag_far05",
            ),
            "far05": binary_metrics(
                case_frame,
                "unavailable_percentile_score",
                "percentile_flag_far05",
            )["far_05"],
            "far10": binary_metrics(
                case_frame,
                "unavailable_percentile_score",
                "percentile_flag_far10",
            )["far_10"],
        },
    }
    boot = bootstrap(case_frame, rank_frame, repeats, 20261126)
    scorecard = {
        "status": f"{source_id}_two_endpoint_method_scored",
        "method": method_id,
        "inputs": {
            name: {
                "path": Path(run_dir.name, name).as_posix(),
                "sha256": sha256(run_dir / name),
            }
            for name in (
                "candidate_predictions.csv",
                "case_scores.csv",
                "fixed_output_candidate_predictions.csv",
                "fixed_output_case_scores.csv",
            )
        },
        "ranking_endpoint": ranking_summary,
        "retrieval_context": retrieval_context,
        "unknown_endpoint": unknown_summary,
        "cluster_bootstrap": boot,
        "claim_boundary": (
            f"{source_id} measured source with frozen cases and true "
            "full/reduced-library execution."
        ),
    }
    return scorecard, rank_frame, case_frame


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--xmatcher-run", type=Path, required=True)
    parser.add_argument("--crystalshift-run", type=Path, required=True)
    parser.add_argument("--xdecomposer-run", type=Path)
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
    rank_tables = {}
    unknown_tables = {}
    methods = [
        ("xmatcher", args.xmatcher_run),
        ("crystalshift", args.crystalshift_run),
    ]
    if args.xdecomposer_run is not None:
        methods.append(("xdecomposer", args.xdecomposer_run))
    for method_id, run_dir in methods:
        scorecard, ranking, unknown = score_method(
            method_id,
            run_dir,
            cases,
            truth,
            args.bootstrap_repeats,
        )
        scorecards[method_id] = scorecard
        rank_tables[method_id] = ranking
        unknown_tables[method_id] = unknown
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

    source_ids = sorted(cases["source"].astype(str).unique())
    if len(source_ids) != 1:
        raise ValueError(f"expected one source, found {source_ids}")
    source_id = source_ids[0]
    summary = {
        "status": f"{source_id}_two_endpoint_summary_complete",
        "source": source_id,
        "queries": len(cases.query_id.unique()),
        "clusters": len(cases.cluster_id.unique()),
        "cases": len(cases),
        "methods": scorecards,
        "cross_method_conclusion": (
            "Methods are interpreted per source and endpoint; candidate rows "
            "are not pooled across acquisitions or candidate libraries."
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
