"""Build the wide score table used by the mechanism diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def normalize_query_id(value: object) -> str:
    text = str(value).strip()
    if text.lower().startswith("sample "):
        return f"sample_{int(text.split()[1]):02d}"
    if text.lower().startswith("sample_"):
        return f"sample_{int(text.split('_', 1)[1]):02d}"
    raise ValueError(f"unexpected query identity: {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    method_ids = [method["id"] for method in registry["methods"]]
    truth = pd.read_csv(args.truth)
    truth = truth.loc[truth["source"].eq("ariadnex_controlled")].copy()
    truth["query_id"] = truth["query_id"].map(normalize_query_id)
    predictions = pd.read_csv(args.predictions)
    predictions["query_id"] = predictions["query_id"].map(normalize_query_id)
    wide = predictions.pivot(
        index=["query_id", "phase_id"],
        columns="method_id",
        values="score",
    ).reset_index()
    missing = set(method_ids) - set(wide.columns)
    if missing:
        raise ValueError(f"prediction methods missing: {sorted(missing)}")
    wide = wide[["query_id", "phase_id", *method_ids]]
    output = truth.merge(
        wide,
        on=["query_id", "phase_id"],
        how="left",
        validate="one_to_one",
    )
    if len(output) != 100 or output[method_ids].isna().any().any():
        raise ValueError("wide external panel table is incomplete")
    output.to_csv(args.out, index=False, lineterminator="\n")
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"wrote {len(output)} rows")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
