#!/usr/bin/env python3
"""Create closed, true-omission and absent-omission Precursor Genome cases."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

SOURCE_ID = "precursor_genome"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def absence_token(query_id: str, candidate_id: str) -> str:
    return hashlib.sha256(
        f"precursor-genome|{query_id}|absent|20261127|{candidate_id}".encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    candidates = pd.read_csv(
        args.dataset / "public" / "candidates.csv",
        dtype=str,
    )
    queries = pd.read_csv(
        args.dataset / "public" / "queries.csv",
        dtype={"query_id": str},
    )
    truth = pd.read_csv(
        args.dataset / "evaluator" / "truth.csv",
        dtype={"query_id": str, "phase_id": str, "present": int},
    )
    candidate_ids = candidates["candidate_id"].tolist()
    if len(candidate_ids) != 20 or len(set(candidate_ids)) != 20:
        raise ValueError("expected 20 unique candidates")
    if len(queries) != 102:
        raise ValueError(f"expected 102 queries, found {len(queries)}")
    if len(truth) != 102 * 20:
        raise ValueError(f"unexpected truth rows: {len(truth)}")

    by_query = {
        query_id: frame.set_index("phase_id")["present"].to_dict()
        for query_id, frame in truth.groupby("query_id", sort=False)
    }
    cases = []
    case_truth = []

    def add_case(
        query_id: str,
        cluster_id: str,
        condition: str,
        omitted: str = "",
    ) -> None:
        available = [
            candidate_id
            for candidate_id in candidate_ids
            if candidate_id != omitted
        ]
        present = by_query[query_id]
        case_id = (
            f"{SOURCE_ID}::{query_id}::{condition}::"
            f"{omitted if omitted else 'none'}"
        )
        cases.append(
            {
                "case_id": case_id,
                "source": SOURCE_ID,
                "query_id": query_id,
                "cluster_id": cluster_id,
                "condition": condition,
                "omitted_phase_id": omitted,
                "unknown_present": int(condition == "omit_present"),
                "candidate_count": len(available),
                "remaining_true_count": sum(
                    present[candidate_id] for candidate_id in available
                ),
                "case_order": len(cases),
            }
        )
        for candidate_id in available:
            case_truth.append(
                {
                    "case_id": case_id,
                    "phase_id": candidate_id,
                    "present": int(present[candidate_id]),
                }
            )

    for query in queries.sort_values("query_id").itertuples(index=False):
        query_id = str(query.query_id)
        cluster_id = str(query.cluster_id)
        present = [
            candidate_id
            for candidate_id in candidate_ids
            if by_query[query_id][candidate_id]
        ]
        absent = [
            candidate_id
            for candidate_id in candidate_ids
            if not by_query[query_id][candidate_id]
        ]
        add_case(query_id, cluster_id, "closed")
        for candidate_id in present:
            add_case(query_id, cluster_id, "omit_present", candidate_id)
        absent_choice = min(
            absent,
            key=lambda candidate_id: absence_token(query_id, candidate_id),
        )
        add_case(query_id, cluster_id, "omit_absent", absent_choice)

    counts = (
        pd.Series([case["condition"] for case in cases])
        .value_counts()
        .to_dict()
    )
    if counts.get("closed") != 102:
        raise ValueError(f"closed case count mismatch: {counts}")
    if counts.get("omit_absent") != 102:
        raise ValueError(f"absent case count mismatch: {counts}")
    if counts.get("omit_present", 0) < 200:
        raise ValueError(f"insufficient true-omission cases: {counts}")

    args.outdir.mkdir(parents=True, exist_ok=False)
    case_frame = pd.DataFrame(cases).sort_values("case_order")
    case_frame.to_csv(
        args.outdir / "cases.csv",
        index=False,
        lineterminator="\n",
    )
    pd.DataFrame(case_truth).sort_values(
        ["case_id", "phase_id"]
    ).to_csv(
        args.outdir / "case_phase_truth.csv",
        index=False,
        lineterminator="\n",
    )

    candidate_structures = candidates[
        ["candidate_id", "reference_profile_file", "reference_profile_sha256"]
    ].sort_values("candidate_id").copy()
    candidate_structures = candidate_structures.rename(
        columns={
            "candidate_id": "phase_id",
            "reference_profile_file": "reference_profile_file",
            "reference_profile_sha256": "reference_profile_sha256",
        }
    )
    candidate_structures.to_csv(
        args.outdir / "candidate_structures.csv",
        index=False,
        lineterminator="\n",
    )

    provenance = pd.read_csv(
        args.dataset / "evaluator" / "candidate_source_provenance.csv",
        dtype=str,
    )
    provenance = provenance.rename(
        columns={
            "candidate_id": "phase_id",
            "phase_id": "source_phase_id",
        }
    )
    provenance.sort_values("phase_id").to_csv(
        args.outdir / "candidate_provenance.csv",
        index=False,
        lineterminator="\n",
    )

    libraries = [
        {
            "library_id": "full",
            "omitted_phase_id": "",
            "candidate_ids": candidate_ids,
            "candidate_count": len(candidate_ids),
        }
    ]
    libraries.extend(
        {
            "library_id": f"minus_{omitted}",
            "omitted_phase_id": omitted,
            "candidate_ids": [
                candidate_id
                for candidate_id in candidate_ids
                if candidate_id != omitted
            ],
            "candidate_count": len(candidate_ids) - 1,
        }
        for omitted in candidate_ids
    )
    manifest = {
        "status": "precursor_genome_cases_frozen",
        "source_id": SOURCE_ID,
        "queries": len(queries),
        "clusters": queries["cluster_id"].nunique(),
        "candidates": len(candidate_ids),
        "cases": len(cases),
        "case_counts": counts,
        "case_phase_truth_rows": len(case_truth),
        "libraries": libraries,
        "claim_boundary": (
            "Cases use source-published reaction truth and query-independent "
            "reference reactions. No method output was inspected."
        ),
    }
    (args.outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
