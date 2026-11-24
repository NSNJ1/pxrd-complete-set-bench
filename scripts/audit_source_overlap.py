"""Audit repeated phase sets and cross-source element overlap."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from pxrd_complete_set_bench.phase_labels import phase_elements


def jaccard(left: set[str], right: set[str]) -> float | None:
    union = left | right
    if not union:
        return None
    return len(left & right) / len(union)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    table = pd.read_csv(args.table)
    required = {"source", "query_id", "cluster_id", "phase_id", "present"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"input columns missing: {sorted(missing)}")

    sources = sorted(table["source"].unique())
    phase_libraries = {
        source: set(table.loc[table["source"].eq(source), "phase_id"])
        for source in sources
    }
    element_libraries = {}
    missing_elements = {}
    for source in sources:
        phases = sorted(phase_libraries[source])
        parsed = {phase_id: phase_elements(source, phase_id) for phase_id in phases}
        element_libraries[source] = {
            element for elements in parsed.values() if elements for element in elements
        }
        missing_elements[source] = sum(value is None for value in parsed.values())

    repeated = {}
    for source in sources:
        local = table.loc[table["source"].eq(source)]
        sets = (
            local.loc[local["present"].eq(1)]
            .groupby(["query_id", "cluster_id"])["phase_id"]
            .agg(lambda values: tuple(sorted(set(values))))
            .reset_index()
        )
        signatures = Counter(sets["phase_id"])
        repeated[source] = {
            "queries": len(sets),
            "unique_positive_sets": len(signatures),
            "queries_with_repeated_set": sum(
                count for count in signatures.values() if count > 1
            ),
            "largest_repeated_set_count": max(signatures.values(), default=0),
        }

    pair_results = {}
    for left_index, left in enumerate(sources):
        for right in sources[left_index + 1 :]:
            pair_results[f"{left}__{right}"] = {
                "phase_id_jaccard": jaccard(
                    phase_libraries[left],
                    phase_libraries[right],
                ),
                "shared_phase_ids": len(phase_libraries[left] & phase_libraries[right]),
                "element_jaccard": jaccard(
                    element_libraries[left],
                    element_libraries[right],
                ),
                "shared_elements": sorted(
                    element_libraries[left] & element_libraries[right]
                ),
            }

    report = {
        "status": "source_overlap_audit",
        "claim_boundary": (
            "Derived identifiers support phase-ID and element-set overlap checks. "
            "They are not a structure-level or prototype-level leakage audit."
        ),
        "input": {
            "path": args.table.as_posix(),
            "sha256": hashlib.sha256(args.table.read_bytes()).hexdigest(),
        },
        "sources": {
            source: {
                "phase_ids": len(phase_libraries[source]),
                "parsed_element_libraries": sorted(element_libraries[source]),
                "phase_ids_without_parsed_elements": missing_elements[source],
                "positive_set_repetition": repeated[source],
            }
            for source in sources
        },
        "pairwise_overlap": pair_results,
        "not_available": [
            "atomic structures for rare-earth MOF CSD identifiers",
            "full structures for several candidate collections",
            "training records for the consumed source cohorts",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report["sources"], ensure_ascii=False, indent=2))
    print(f"sha256={hashlib.sha256(args.out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
