#!/usr/bin/env python3
"""Summarize eligible reaction clusters in the Precursor Genome ledger."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def phase_rows(sample: dict) -> pd.DataFrame:
    phases = (sample.get("outcome") or {}).get("phases") or []
    return pd.DataFrame(
        [
            {
                "sample_id": sample["sample_id"],
                "phase_id": phase["name"],
                "weight_percent": float(phase["weight_percent"]),
            }
            for phase in phases
        ],
        columns=["sample_id", "phase_id", "weight_percent"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    samples = ledger["samples"]
    args.outdir.mkdir(parents=True, exist_ok=True)

    sample_rows = []
    all_phase_rows = []
    for sample in samples:
        sample_id = sample["sample_id"]
        xrd = (sample.get("characterization") or {}).get("xrd") or {}
        scans = xrd.get("scans") or []
        active_scan_index = sample.get("active_scan_index")
        active_scan = (
            scans[active_scan_index]
            if isinstance(active_scan_index, int)
            and 0 <= active_scan_index < len(scans)
            else None
        )
        active_case = None
        if active_scan and active_scan.get("refinement_cases"):
            case_index = active_scan.get("active_case_index")
            if isinstance(case_index, int) and 0 <= case_index < len(
                active_scan["refinement_cases"]
            ):
                active_case = active_scan["refinement_cases"][case_index]
        verification = (active_case or {}).get("verification") or {}
        phases = phase_rows(sample)
        if not phases.empty:
            all_phase_rows.append(phases)
        phase_names = sorted(phases["phase_id"].tolist())
        min_weight = (
            float(phases["weight_percent"].min()) if not phases.empty else None
        )
        sample_rows.append(
            {
                "sample_id": sample_id,
                "target_compound": sample.get("target_compound"),
                "target_stoichiometry": sample.get("target_stoichiometry"),
                "reaction_category": (sample.get("outcome") or {}).get(
                    "reaction_category"
                ),
                "phase_count": len(phase_names),
                "phase_names": "|".join(phase_names),
                "min_weight_percent": min_weight,
                "physical_failure": sample.get("physical_failure") is not None,
                "scan_count": len(scans),
                "active_scan_index": active_scan_index,
                "scan_filename": (active_scan or {}).get("filename"),
                "scan_status": (active_scan or {}).get("status"),
                "active_case_index": (active_scan or {}).get("active_case_index"),
                "refinement_rwp": (active_case or {}).get("rwp"),
                "pkl_path": (active_case or {}).get("pkl_path"),
                "quality_score": verification.get("human_quality_score"),
                "accepted": verification.get("is_accepted"),
                "elements_present": "|".join(
                    (sample.get("synthesis") or {}).get("elements_present") or []
                ),
            }
        )

    sample_frame = pd.DataFrame(sample_rows)
    phase_frame = (
        pd.concat(all_phase_rows, ignore_index=True)
        if all_phase_rows
        else pd.DataFrame(
            columns=["sample_id", "phase_id", "weight_percent"]
        )
    )
    sample_frame.to_csv(
        args.outdir / "sample_summary.csv",
        index=False,
        lineterminator="\n",
    )
    phase_frame.to_csv(
        args.outdir / "sample_phases.csv",
        index=False,
        lineterminator="\n",
    )
    phase_frequency = (
        phase_frame.groupby("phase_id")
        .agg(
            sample_count=("sample_id", "nunique"),
            median_weight_percent=("weight_percent", "median"),
            minimum_weight_percent=("weight_percent", "min"),
        )
        .reset_index()
        .sort_values(["sample_count", "phase_id"], ascending=[False, True])
    )
    phase_frequency.to_csv(
        args.outdir / "phase_frequency.csv",
        index=False,
        lineterminator="\n",
    )

    eligible = sample_frame[
        sample_frame["accepted"].eq(True)
        & sample_frame["quality_score"].le(2)
        & sample_frame["phase_count"].between(2, 4)
        & sample_frame["physical_failure"].eq(False)
        & sample_frame["scan_filename"].notna()
    ]
    stats = {
        "samples": len(sample_frame),
        "phase_rows": len(phase_frame),
        "unique_phases": phase_frame["phase_id"].nunique(),
        "phase_count_distribution": dict(
            sorted(Counter(sample_frame["phase_count"]).items())
        ),
        "quality_score_distribution": dict(
            sorted(
                Counter(
                    sample_frame["quality_score"]
                    .astype("string")
                    .fillna("missing")
                ).items(),
            )
        ),
        "accepted_distribution": dict(
            sorted(
                Counter(
                    sample_frame["accepted"]
                    .astype("string")
                    .fillna("missing")
                ).items()
            )
        ),
        "eligible_2_to_4_phases_accepted_q1_q2": len(eligible),
        "eligible_unique_phases": phase_frame.loc[
            phase_frame["sample_id"].isin(eligible["sample_id"]),
            "phase_id",
        ].nunique(),
        "eligible_phase_count_distribution": dict(
            sorted(Counter(eligible["phase_count"]).items())
        ),
    }
    (args.outdir / "analysis.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
