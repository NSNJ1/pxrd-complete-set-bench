#!/usr/bin/env python3
"""Freeze a top-20 phase benchmark from the Precursor Genome ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

import pandas as pd
from remotezip import RemoteZip

RAW_SCANS_URL = (
    "https://zenodo.org/api/records/21285546/files/raw_scans.zip/content"
)
REFINEMENT_PKLS_URL = (
    "https://zenodo.org/api/records/21285546/files/refinement_pkls.zip/content"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def active_scan(sample: dict) -> tuple[dict | None, dict | None]:
    xrd = (sample.get("characterization") or {}).get("xrd") or {}
    scans = xrd.get("scans") or []
    active_index = sample.get("active_scan_index")
    if not isinstance(active_index, int) or not (
        0 <= active_index < len(scans)
    ):
        return None, None
    scan = scans[active_index]
    cases = scan.get("refinement_cases") or []
    case_index = scan.get("active_case_index")
    if not isinstance(case_index, int) or not (0 <= case_index < len(cases)):
        return scan, None
    return scan, cases[case_index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--minimum-queries", type=int, default=60)
    args = parser.parse_args()

    ledger_path = args.ledger.resolve()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    args.outdir.mkdir(parents=True, exist_ok=True)

    raw_names = set(RemoteZip(RAW_SCANS_URL).namelist())
    pkl_names = set(RemoteZip(REFINEMENT_PKLS_URL).namelist())
    raw_by_basename = {
        PurePosixPath(name).name: name
        for name in raw_names
        if name.endswith(".xrdml")
    }

    records = []
    for sample in ledger["samples"]:
        scan, case = active_scan(sample)
        phases = (sample.get("outcome") or {}).get("phases") or []
        verification = (case or {}).get("verification") or {}
        scan_filename = (scan or {}).get("filename") or ""
        pkl_path = (case or {}).get("pkl_path") or ""
        phase_weights = {
            str(row["name"]): float(row["weight_percent"])
            for row in phases
        }
        case_weights = (case or {}).get("phase_weights") or {}
        records.append(
            {
                "sample_id": sample["sample_id"],
                "target_compound": sample.get("target_compound"),
                "reaction_category": (sample.get("outcome") or {}).get(
                    "reaction_category"
                ),
                "phase_count": len(phase_weights),
                "phase_ids": "|".join(sorted(phase_weights)),
                "phase_weights_json": json.dumps(
                    phase_weights,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "minimum_weight_percent": (
                    min(phase_weights.values()) if phase_weights else None
                ),
                "quality_score": verification.get("human_quality_score"),
                "accepted": verification.get("is_accepted"),
                "physical_failure": sample.get("physical_failure") is not None,
                "scan_filename": scan_filename,
                "scan_archive_member": raw_by_basename.get(scan_filename),
                "pkl_path": pkl_path,
                "pkl_archive_member": pkl_path if pkl_path in pkl_names else None,
                "truth_matches_active_case": (
                    set(phase_weights) == set(case_weights)
                    and all(
                        abs(
                            phase_weights[phase_id]
                            - float(case_weights[phase_id])
                        )
                        <= 5e-5
                        for phase_id in phase_weights
                    )
                ),
            }
        )

    frame = pd.DataFrame(records)
    eligible = frame[
        frame["accepted"].eq(True)
        & frame["quality_score"].le(2)
        & frame["phase_count"].between(2, 4)
        & frame["physical_failure"].eq(False)
        & frame["scan_archive_member"].notna()
        & frame["pkl_archive_member"].notna()
        & frame["truth_matches_active_case"].eq(True)
    ].copy()

    phase_rows = []
    for row in eligible.itertuples(index=False):
        weights = json.loads(row.phase_weights_json)
        for phase_id, weight in weights.items():
            phase_rows.append(
                {
                    "sample_id": row.sample_id,
                    "phase_id": phase_id,
                    "weight_percent": weight,
                }
            )
    phase_frame = pd.DataFrame(phase_rows)
    frequency = (
        phase_frame.groupby("phase_id")
        .agg(
            sample_count=("sample_id", "nunique"),
            median_weight_percent=("weight_percent", "median"),
        )
        .reset_index()
        .sort_values(
            ["sample_count", "phase_id"],
            ascending=[False, True],
        )
    )
    top_phases = frequency.head(args.top_n)["phase_id"].tolist()
    top_set = set(top_phases)
    phase_sets = phase_frame.groupby("sample_id")["phase_id"].agg(set)
    covered = eligible[
        eligible["sample_id"].map(
            lambda sample_id: set(phase_sets[sample_id]).issubset(top_set)
        )
    ].copy()

    reference_rows = []
    used_samples = set()
    for phase_id in top_phases:
        candidates = phase_frame[phase_frame["phase_id"].eq(phase_id)].merge(
            eligible[
                [
                    "sample_id",
                    "quality_score",
                    "phase_count",
                    "scan_archive_member",
                    "pkl_archive_member",
                ]
            ],
            on="sample_id",
            how="inner",
        )
        candidates["reuse_penalty"] = candidates["sample_id"].isin(
            used_samples
        )
        candidates["manual_pickle_penalty"] = candidates[
            "pkl_archive_member"
        ].str.endswith("_manual.pkl")
        candidates = candidates.sort_values(
            [
                "reuse_penalty",
                "manual_pickle_penalty",
                "quality_score",
                "phase_count",
                "weight_percent",
                "sample_id",
            ],
            ascending=[True, True, True, True, False, True],
        )
        selected = candidates.iloc[0]
        used_samples.add(str(selected["sample_id"]))
        reference_rows.append(
            {
                "phase_id": phase_id,
                "reference_sample_id": str(selected["sample_id"]),
                "reference_phase_weight": float(selected["weight_percent"]),
                "reference_scan_member": str(selected["scan_archive_member"]),
                "reference_pkl_member": str(selected["pkl_archive_member"]),
                "manual_pickle_penalty": bool(
                    selected["manual_pickle_penalty"]
                ),
                "quality_score": int(selected["quality_score"]),
                "reference_phase_count": int(selected["phase_count"]),
            }
        )

    reference_frame = pd.DataFrame(reference_rows)
    queries = covered[~covered["sample_id"].isin(used_samples)].copy()
    if len(reference_frame) != args.top_n:
        raise ValueError("incomplete phase-reference mapping")
    if len(queries) < args.minimum_queries:
        raise ValueError(
            f"only {len(queries)} independent queries after reference exclusion"
        )
    if not queries["phase_ids"].map(
        lambda value: set(str(value).split("|")).issubset(top_set)
    ).all():
        raise ValueError("query phase falls outside the selected library")

    eligible.to_csv(
        args.outdir / "eligible_samples.csv",
        index=False,
        lineterminator="\n",
    )
    frequency.to_csv(
        args.outdir / "phase_frequency.csv",
        index=False,
        lineterminator="\n",
    )
    reference_frame.to_csv(
        args.outdir / "reference_manifest.csv",
        index=False,
        lineterminator="\n",
    )
    queries.sort_values("sample_id").to_csv(
        args.outdir / "query_manifest.csv",
        index=False,
        lineterminator="\n",
    )

    manifest = {
        "status": "precursor_genome_selection_frozen",
        "source": {
            "title": "Precursor Genome",
            "record": "21285546",
            "doi": "10.5281/zenodo.21285546",
            "license": "CC BY 4.0",
            "ledger_sha256": sha256(ledger_path),
        },
        "admission": {
            "ledger_samples": len(frame),
            "eligible_2_to_4_phase_q1_q2_samples": len(eligible),
            "top_phase_count": len(top_phases),
            "samples_fully_covered_by_top_library": len(covered),
            "reference_samples": len(used_samples),
            "independent_query_clusters": len(queries),
            "phase_count_distribution": dict(
                sorted(Counter(queries["phase_count"]).items())
            ),
            "quality_distribution": dict(
                sorted(Counter(queries["quality_score"]).items())
            ),
            "minimum_query_phase_weight": float(
                phase_frame[
                    phase_frame["sample_id"].isin(queries["sample_id"])
                ]["weight_percent"].min()
            ),
        },
        "candidate_library": top_phases,
        "reference_selection_rule": (
            "Select a unique source sample per candidate phase, preferring an "
            "unseen non-manual reference pickle, quality 1, fewer phases, "
            "higher fitted phase weight, then sample ID."
        ),
        "query_selection_rule": (
            "Use every eligible active-scan reaction whose complete truth lies "
            "inside the top-20 library, except samples used to construct "
            "candidate reference profiles."
        ),
        "claim_boundary": (
            "Previously unused external measured retrospective holdout. "
            "One scan per physical reaction; repeated scans are not treated as "
            "independent samples."
        ),
    }
    (args.outdir / "SELECTION_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
