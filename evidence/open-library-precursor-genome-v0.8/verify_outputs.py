#!/usr/bin/env python3
"""Verify independent method-output coverage and canonical hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = json.loads(
    (ROOT / "EXPECTED_OUTPUT_HASHES.json").read_text(encoding="utf-8")
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--crystalshift", type=Path, required=True)
    parser.add_argument("--xdecomposer", type=Path)
    args = parser.parse_args()

    roots = {
        "profile_baseline": args.profile,
        "crystalshift": args.crystalshift,
    }
    if args.xdecomposer is not None:
        roots["xdecomposer"] = args.xdecomposer
    report = {"status": "independent_output_check", "methods": {}}
    passed = True
    for method, root in roots.items():
        method_report = {"files": {}, "hash_match": True}
        expected_files = {
            filename: expected_hash
            for filename, expected_hash in EXPECTED[method].items()
            if isinstance(expected_hash, str)
        }
        for filename, expected_hash in expected_files.items():
            path = root / filename
            observed_hash = sha256(path) if path.is_file() else None
            match = observed_hash == expected_hash
            method_report["files"][filename] = {
                "exists": path.is_file(),
                "expected_sha256": expected_hash,
                "observed_sha256": observed_hash,
                "match": match,
            }
            method_report["hash_match"] &= match
            passed &= match
        expected_libraries = EXPECTED[method].get("library_output_hashes")
        if expected_libraries is not None:
            observed_libraries = {}
            for library_id, expected_files in expected_libraries.items():
                observed_files = {}
                for filename, expected_hash in expected_files.items():
                    hash_name = {
                        "predictions_sha256": "predictions.csv",
                        "sets_sha256": "sets.csv",
                        "unknown_sha256": "query_unknown.csv",
                    }[filename]
                    path = root / library_id / hash_name
                    observed_hash = sha256(path) if path.is_file() else None
                    observed_files[filename] = observed_hash
                    match = observed_hash == expected_hash
                    method_report["hash_match"] &= match
                    passed &= match
                observed_libraries[library_id] = observed_files
            method_report["library_files"] = observed_libraries
        report["methods"][method] = method_report

    crystal_manifest = json.loads(
        (args.crystalshift / "execution_status.json").read_text(
            encoding="utf-8"
        )
    )
    library_hashes = crystal_manifest.get("library_output_hashes", {})
    report["methods"]["crystalshift"]["libraries"] = len(library_hashes)
    report["methods"]["crystalshift"]["library_hash_entries"] = sum(
        len(values) for values in library_hashes.values()
    )
    passed &= set(library_hashes) == {
        "full",
        *{
            f"minus_{phase}"
            for phase in (
                "ag_sg225_icsd604631",
                "alho3_sg14_icsd184003",
                "baco3_sg62_icsd166091",
                "bao2_sg139_icsd80750",
                "bho3_sg2_icsd61354",
                "caco3_sg167_icsd166364",
                "cuo_sg9_icsd69758",
                "ga792o12_sg12_icsd63907",
                "in2o3_sg206_icsd190344",
                "laho3_sg176_icsd167480",
                "li2co3_sg15_icsd16713",
                "mgo_sg225_icsd104844",
                "mn2o3_sg206_icsd9091",
                "mno2_sg136_icsd643186",
                "moo3_sg62_icsd166362",
                "sb2o3_sg227_icsd1944",
                "srco3_sg62_icsd56099",
                "v2o5_sg59_icsd40488",
                "y2o3_sg206_icsd192862",
                "zro2_sg14_icsd157403",
            )
        }
    }
    report["status"] = (
        "independent_output_check_passed"
        if passed
        else "independent_output_check_failed"
    )
    output = ROOT / "INDEPENDENT_OUTPUT_CHECK.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
