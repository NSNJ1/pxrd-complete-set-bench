"""Assemble the frozen six-method AriadneX prediction table."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

METHOD_FILES = (
    ("deterministic_random", "deterministic_random_predictions.csv"),
    ("global_sqrt_pearson", "global_sqrt_pearson_predictions.csv"),
    ("window_sqrt_pearson", "window_sqrt_pearson_predictions.csv"),
    ("anchored_set_strict", "aer_strict_predictions.csv"),
    ("crystalshift", "crystalshift_predictions.csv"),
    ("xrd_autoanalyzer", "xrd_autoanalyzer_predictions.csv"),
)

QUERIES = tuple(f"sample_{index:02d}" for index in range(1, 26))
PHASES = ("A", "B", "C", "D")


def normalize_query_id(value: str) -> str:
    text = value.strip()
    if text.lower().startswith("sample "):
        return f"sample_{int(text.split()[1]):02d}"
    if text.lower().startswith("sample_"):
        return f"sample_{int(text.split('_', 1)[1]):02d}"
    raise ValueError(f"unexpected query identity: {value!r}")


def read_predictions(path: Path, method_id: str) -> list[dict[str, str]]:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"query_id", "phase_id", "score"}.issubset(reader.fieldnames or []):
            raise ValueError(f"missing prediction columns in {path}")
        for row in reader:
            query = normalize_query_id(row["query_id"])
            phase = row["phase_id"].strip()
            key = (query, phase)
            if phase not in PHASES or key in seen:
                raise ValueError(f"invalid or duplicate prediction in {path}: {row}")
            seen.add(key)
            rows.append(
                {
                    "method_id": method_id,
                    "query_id": query,
                    "phase_id": phase,
                    "score": row["score"].strip(),
                }
            )
    expected = {(query, phase) for query in QUERIES for phase in PHASES}
    if seen != expected:
        raise ValueError(f"incomplete prediction grid in {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for method_id, filename in METHOD_FILES:
        rows.extend(read_predictions(args.predictions_dir / filename, method_id))
    rows.sort(key=lambda row: (row["method_id"], row["query_id"], row["phase_id"]))
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["method_id", "query_id", "phase_id", "score"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"wrote {len(rows)} prediction rows")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
