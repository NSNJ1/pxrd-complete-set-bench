#!/usr/bin/env python3
"""Audit the frozen Precursor Genome benchmark and method outputs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset_v7"
CASES = ROOT / "cases_v8"
SCORES = ROOT / "scores_v8"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def absence_token(query_id: str, candidate_id: str) -> str:
    value = (
        f"precursor-genome|{query_id}|absent|20261127|{candidate_id}"
    ).encode()
    return hashlib.sha256(value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    checks: list[dict[str, object]] = []

    def record(name: str, condition: bool, detail: str) -> None:
        require(condition, f"{name}: {detail}")
        checks.append({"check": name, "passed": True, "detail": detail})

    selection = load_json(ROOT / "selection_v3" / "SELECTION_MANIFEST.json")
    record(
        "selection_status",
        selection["status"] == "precursor_genome_selection_frozen",
        selection["status"],
    )
    record(
        "selected_counts",
        selection["admission"]["independent_query_clusters"] == 102
        and selection["admission"]["reference_samples"] == 20,
        json.dumps(selection["admission"], sort_keys=True),
    )
    record(
        "prior_project_overlap_claim",
        selection["claim_correction"]["prior_project_query_count"] == 416
        and selection["claim_correction"]["query_id_overlap"] == 77
        and selection["claim_correction"]["new_query_count"] == 25
        and "Previously used by this project"
        in selection["claim_boundary"],
        selection["claim_correction"],
    )

    overlap = load_json(ROOT / "PRIOR_PROJECT_OVERLAP_20261127.json")
    record(
        "prior_project_overlap_counts",
        overlap["prior_project"]["query_count"] == 416
        and overlap["open_library_panel"]["query_count"] == 102
        and overlap["overlap"]["exact_query_id_overlap"] == 77
        and overlap["overlap"]["new_query_ids"] == 25,
        overlap["overlap"],
    )
    prior_ids_path = ROOT / overlap["prior_project"]["query_ids_file"]
    prior_ids = {
        line.strip()
        for line in prior_ids_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    record(
        "prior_query_id_file_sha256",
        sha256(prior_ids_path)
        == overlap["prior_project"]["query_ids_file_sha256"],
        overlap["prior_project"]["query_ids_file_sha256"],
    )
    current_queries = csv_rows(DATASET / "public" / "queries.csv")
    current_ids = {row["query_id"] for row in current_queries}
    record(
        "prior_project_overlap_recount",
        len(prior_ids) == 416
        and len(current_ids) == 102
        and len(prior_ids.intersection(current_ids)) == 77
        and len(current_ids.difference(prior_ids)) == 25,
        {
            "prior": len(prior_ids),
            "current": len(current_ids),
            "overlap": len(prior_ids.intersection(current_ids)),
            "new": len(current_ids.difference(prior_ids)),
        },
    )

    record_metadata = load_json(ROOT / "zenodo_record_21285546.json")
    record(
        "zenodo_record_license",
        record_metadata["metadata"]["license"]["id"] == "cc-by-4.0",
        record_metadata["metadata"]["license"]["id"],
    )
    record(
        "zenodo_record_version",
        record_metadata["metadata"]["version"] == "1.0",
        record_metadata["metadata"]["version"],
    )
    source_files = {
        item["key"]: item["checksum"]
        for item in record_metadata["files"]
    }
    record(
        "raw_scan_archive_checksum",
        source_files["raw_scans.zip"]
        == "md5:e22405e733fc79ff4b14b679f87a33d5",
        source_files["raw_scans.zip"],
    )
    record(
        "refinement_archive_checksum",
        source_files["refinement_pkls.zip"]
        == "md5:49447823b4e017524fd963ec3734af74",
        source_files["refinement_pkls.zip"],
    )

    dataset_manifest = load_json(DATASET / "manifest.json")
    expected_ledger_hash = (
        "f8b8aabb5b8718ad912075b9aa10373a5e81659b496348f14c926e432eb42dac"
    )
    record(
        "recorded_source_ledger_hash",
        dataset_manifest["source"]["ledger_sha256"] == expected_ledger_hash,
        dataset_manifest["source"]["ledger_sha256"],
    )
    ledger_override = os.environ.get("PRECURSOR_GENOME_LEDGER")
    if ledger_override is not None:
        ledger_path = Path(ledger_override)
        record("source_ledger_present", ledger_path.is_file(), str(ledger_path))
        record(
            "source_ledger_sha256",
            sha256(ledger_path) == expected_ledger_hash,
            sha256(ledger_path),
        )
    record(
        "dataset_reuse_claim",
        "Previously used by this project" in dataset_manifest["claim_boundary"],
        dataset_manifest["claim_boundary"],
    )
    dataset_files = {
        "candidate_manifest_sha256": DATASET / "public" / "candidates.csv",
        "candidate_sticks_sha256": (
            DATASET / "public" / "candidate_sticks.csv"
        ),
        "query_manifest_sha256": DATASET / "public" / "queries.csv",
        "query_metadata_sha256": (
            DATASET / "evaluator" / "query_metadata.csv"
        ),
        "truth_sha256": DATASET / "evaluator" / "truth.csv",
    }
    for key, path in dataset_files.items():
        observed = sha256(path)
        record(key, dataset_manifest[key] == observed, observed)

    public_candidates = csv_rows(DATASET / "public" / "candidates.csv")
    record(
        "public_candidate_header",
        list(public_candidates[0])
        == [
            "candidate_id",
            "reference_profile_file",
            "reference_profile_sha256",
        ],
        str(list(public_candidates[0])),
    )
    record(
        "public_candidate_count",
        len(public_candidates) == 20,
        str(len(public_candidates)),
    )
    for row in public_candidates:
        profile_path = DATASET / row["reference_profile_file"]
        record(
            f"candidate_profile_exists:{row['candidate_id']}",
            profile_path.is_file(),
            row["reference_profile_file"],
        )
        record(
            f"candidate_profile_sha256:{row['candidate_id']}",
            sha256(profile_path) == row["reference_profile_sha256"],
            row["reference_profile_sha256"],
        )

    public_queries = csv_rows(DATASET / "public" / "queries.csv")
    record(
        "public_query_header",
        list(public_queries[0])
        == [
            "query_id",
            "cluster_id",
            "spectrum_file",
            "wavelength_angstrom",
        ],
        str(list(public_queries[0])),
    )
    record(
        "public_query_count",
        len(public_queries) == 102,
        str(len(public_queries)),
    )
    record(
        "query_clusters",
        len({row["query_id"] for row in public_queries}) == 102
        and len({row["cluster_id"] for row in public_queries}) == 102,
        "102 query IDs and 102 clusters",
    )
    record(
        "query_wavelength",
        {row["wavelength_angstrom"] for row in public_queries}
        == {"1.5405980"},
        str({row["wavelength_angstrom"] for row in public_queries}),
    )
    for row in public_queries:
        record(
            f"public_spectrum_exists:{row['query_id']}",
            (DATASET / row["spectrum_file"]).is_file(),
            row["spectrum_file"],
        )

    query_metadata = csv_rows(DATASET / "evaluator" / "query_metadata.csv")
    record(
        "query_metadata_header",
        list(query_metadata[0])
        == [
            "query_id",
            "cluster_id",
            "quality_score",
            "phase_count",
            "scan_archive_member",
            "scan_sha256",
        ],
        str(list(query_metadata[0])),
    )
    record(
        "query_metadata_count",
        len(query_metadata) == 102,
        str(len(query_metadata)),
    )
    record(
        "query_metadata_ids",
        {row["query_id"] for row in query_metadata}
        == {row["query_id"] for row in public_queries},
        "query metadata and public query IDs match",
    )

    query_manifest = csv_rows(
        ROOT / "selection_v3" / "query_manifest.csv"
    )
    reference_manifest = csv_rows(
        ROOT / "selection_v3" / "reference_manifest.csv"
    )
    query_ids = {row["sample_id"] for row in query_manifest}
    reference_ids = {
        row["reference_sample_id"] for row in reference_manifest
    }
    record(
        "reference_query_disjoint",
        not query_ids.intersection(reference_ids),
        (
            f"{len(query_ids)} query IDs; "
            f"{len(reference_ids)} reference IDs; overlap 0"
        ),
    )
    record(
        "unique_reference_reactions",
        len(reference_ids) == 20,
        str(len(reference_ids)),
    )

    dataset_truth = csv_rows(DATASET / "evaluator" / "truth.csv")
    truth_by_query: dict[str, dict[str, int]] = {}
    for row in dataset_truth:
        truth_by_query.setdefault(row["query_id"], {})[row["phase_id"]] = int(
            row["present"]
        )
    record(
        "dataset_truth_unique",
        len(truth_by_query) == 102
        and all(len(values) == 20 for values in truth_by_query.values()),
        "102 queries with 20 unique candidate labels each",
    )
    record(
        "dataset_truth_rows",
        len(dataset_truth) == 2040,
        str(len(dataset_truth)),
    )
    record(
        "truth_phase_counts",
        Counter(
            sum(values.values()) for values in truth_by_query.values()
        )
        == {2: 92, 3: 10},
        str(
            Counter(
                sum(values.values()) for values in truth_by_query.values()
            )
        ),
    )

    cases_manifest = load_json(CASES / "manifest.json")
    cases = csv_rows(CASES / "cases.csv")
    case_truth = csv_rows(CASES / "case_phase_truth.csv")
    candidate_ids = sorted(
        row["candidate_id"] for row in public_candidates
    )
    record(
        "case_status",
        cases_manifest["status"] == "precursor_genome_cases_frozen",
        cases_manifest["status"],
    )
    record(
        "case_counts",
        len(cases) == 418
        and Counter(row["condition"] for row in cases)
        == {
            "closed": 102,
            "omit_present": 214,
            "omit_absent": 102,
        },
        str(Counter(row["condition"] for row in cases)),
    )
    record(
        "case_ids_unique",
        len({row["case_id"] for row in cases}) == 418,
        "418 unique case IDs",
    )
    record(
        "case_truth_rows",
        len(case_truth) == 8044,
        str(len(case_truth)),
    )
    record(
        "method_candidate_header",
        list(csv_rows(CASES / "candidate_structures.csv")[0])
        == [
            "phase_id",
            "reference_profile_file",
            "reference_profile_sha256",
        ],
        str(list(csv_rows(CASES / "candidate_structures.csv")[0])),
    )

    truth_by_case: dict[str, dict[str, int]] = {}
    for row in case_truth:
        truth_by_case.setdefault(row["case_id"], {})[row["phase_id"]] = int(
            row["present"]
        )
    record(
        "case_truth_unique",
        sum(len(values) for values in truth_by_case.values())
        == len(case_truth),
        "no repeated case-phase truth keys",
    )

    absent_rows = {
        row["query_id"]: row for row in cases if row["condition"] == "omit_absent"
    }
    record(
        "one_absent_control_per_query",
        len(absent_rows) == 102,
        str(len(absent_rows)),
    )
    for case in cases:
        query_id = case["query_id"]
        omitted = case["omitted_phase_id"]
        expected_available = [
            candidate_id
            for candidate_id in candidate_ids
            if candidate_id != omitted
        ]
        observed_truth = truth_by_case[case["case_id"]]
        record(
            f"case_truth_coverage:{case['case_id']}",
            set(observed_truth) == set(expected_available),
            f"{len(observed_truth)} rows",
        )
        expected_present = truth_by_query[query_id]
        for phase_id in expected_available:
            expected = expected_present[phase_id]
            record(
                f"case_truth_label:{case['case_id']}:{phase_id}",
                observed_truth[phase_id] == expected,
                str(expected),
            )
        record(
            f"case_remaining_true_count:{case['case_id']}",
            int(case["remaining_true_count"])
            == sum(expected_present[item] for item in expected_available),
            case["remaining_true_count"],
        )
        expected_unknown = int(case["condition"] == "omit_present")
        record(
            f"case_unknown_label:{case['case_id']}",
            int(case["unknown_present"]) == expected_unknown,
            str(expected_unknown),
        )
        if case["condition"] == "omit_present":
            record(
                f"omitted_was_present:{case['case_id']}",
                expected_present[omitted] == 1,
                omitted,
            )
        if case["condition"] == "omit_absent":
            absent_candidates = [
                phase_id
                for phase_id in candidate_ids
                if expected_present[phase_id] == 0
            ]
            expected_choice = min(
                absent_candidates,
                key=lambda item: absence_token(query_id, item),
            )
            record(
                f"absent_control_choice:{case['case_id']}",
                omitted == expected_choice,
                omitted,
            )

    libraries = cases_manifest["libraries"]
    record(
        "library_count",
        len(libraries) == 21,
        str(len(libraries)),
    )
    for library in libraries:
        omitted = library["omitted_phase_id"]
        expected_ids = [
            candidate_id
            for candidate_id in candidate_ids
            if candidate_id != omitted
        ]
        record(
            f"library_members:{library['library_id']}",
            library["candidate_ids"] == expected_ids
            and library["candidate_count"] == len(expected_ids),
            str(len(expected_ids)),
        )

    run_pairs = {
        "profile_baseline": (
            ROOT / "profile_baseline_run_v8",
            ROOT / "profile_baseline_repeat_v2",
        ),
        "crystalshift": (
            ROOT / "crystalshift_run_v8",
            ROOT / "crystalshift_run_v2",
        ),
        "xdecomposer": (
            ROOT / "xdecomposer_run_v8",
            ROOT / "xdecomposer_repeat_v2",
        ),
    }
    output_names = (
        "candidate_predictions.csv",
        "case_scores.csv",
        "fixed_output_candidate_predictions.csv",
        "fixed_output_case_scores.csv",
    )
    for method, (primary, repeat) in run_pairs.items():
        status = load_json(primary / "execution_status.json")
        record(
            f"{method}_completion",
            status["queries"] == 102
            and status["cases"] == 418
            and status.get(
                "candidate_truth_rows",
                status.get("candidate_rows"),
            )
            == 8044,
            json.dumps(
                {
                    "queries": status["queries"],
                    "cases": status["cases"],
                    "candidate_rows": status.get(
                        "candidate_truth_rows",
                        status.get("candidate_rows"),
                    ),
                }
            ),
        )
        for filename in output_names:
            primary_hash = sha256(primary / filename)
            repeat_hash = sha256(repeat / filename)
            record(
                f"{method}:repeat:{filename}",
                primary_hash == repeat_hash,
                primary_hash,
            )

    score_summary = load_json(SCORES / "summary.json")
    record(
        "score_status",
        score_summary["status"]
        == "precursor_genome_two_endpoint_summary_complete",
        score_summary["status"],
    )
    record(
        "score_source_size",
        score_summary["queries"] == 102
        and score_summary["clusters"] == 102
        and score_summary["cases"] == 418,
        json.dumps(
            {
                "queries": score_summary["queries"],
                "clusters": score_summary["clusters"],
                "cases": score_summary["cases"],
            }
        ),
    )
    for method, card in score_summary["methods"].items():
        boot = card["cluster_bootstrap"]
        record(
            f"score_bootstrap:{method}",
            boot["repeats_requested"] == 10_000
            and boot["clusters"] == 102
            and all(
                interval["finite_replicates"] == 10_000
                for interval in boot["intervals"].values()
            ),
            json.dumps(
                {
                    key: value["finite_replicates"]
                    for key, value in boot["intervals"].items()
                }
            ),
        )
        actual = card["unknown_endpoint"]["actual"]["all"]["auroc"]
        fixed = card["unknown_endpoint"]["fixed_full_residual"]["all"][
            "auroc"
        ]
        record(
            f"score_finite:{method}",
            math.isfinite(actual) and math.isfinite(fixed),
            f"actual={actual}; fixed={fixed}",
        )

    sensitivity = load_json(ROOT / "sensitivity_v8" / "summary.json")
    record(
        "sensitivity_status",
        sensitivity["status"] == "precursor_genome_sensitivity_complete",
        sensitivity["status"],
    )
    expected_sensitivity = {
        "quality_1": (80, 328, 168),
        "unreacted_only": (87, 348, 174),
        "omitted_weight_ge_005": (102, 410, 206),
    }
    for scenario, expected_counts in expected_sensitivity.items():
        observed = sensitivity["scenarios"][scenario]
        record(
            f"sensitivity_counts:{scenario}",
            (
                observed["queries"],
                observed["cases"],
                observed["true_omission_cases"],
            )
            == expected_counts,
            str(
                (
                    observed["queries"],
                    observed["cases"],
                    observed["true_omission_cases"],
                )
            ),
        )
        for method, card in observed["methods"].items():
            interval = card["bootstrap"]["actual_minus_fixed"]
            record(
                f"sensitivity_interval:{scenario}:{method}",
                interval["finite_replicates"] == 10_000
                and interval["ci95"][0] > 0,
                str(interval["ci95"]),
            )
        order_interval = observed["methods"]["crystalshift"]["bootstrap"][
            "true_subset_order_change_rate"
        ]
        if scenario == "unreacted_only":
            record(
                "unreacted_order_endpoint_not_estimable",
                order_interval.get("status") == "not_estimable"
                and order_interval["finite_replicates"] == 0,
                json.dumps(order_interval),
            )
        else:
            record(
                f"order_interval_estimable:{scenario}",
                order_interval["finite_replicates"] > 0,
                str(order_interval["finite_replicates"]),
            )

    audit = {
        "status": "precursor_genome_release_audit_passed",
        "dataset": "dataset_v7",
        "cases": "cases_v8",
        "scores": "scores_v8",
        "checks_passed": len(checks),
        "checks": checks,
        "claim_boundary": (
            "Previously used by this project in the closed-library benchmark. "
            "New for the open-library intervention only: 77/102 query IDs "
            "overlap the earlier cohort and 25 are new. Reference reactions are "
            "disjoint from query reactions, and one active scan represents each "
            "physical reaction."
        ),
    }
    output = ROOT / "RELEASE_AUDIT_20261127.json"
    output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "checks_passed": len(checks),
                "output": str(output),
                "output_sha256": sha256(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
