#!/usr/bin/env python3
"""Run CrystalShift on a frozen full-library and leave-one-out panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_SOURCE_ID = "dara_precursor_mixtures"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_outputs(
    library_dir: Path,
    query_count: int,
    candidate_count: int,
) -> tuple[dict[tuple[str, str], float], dict[str, float], dict[str, str]]:
    prediction_path = library_dir / "predictions.csv"
    set_path = library_dir / "sets.csv"
    unknown_path = library_dir / "query_unknown.csv"
    predictions = pd.read_csv(prediction_path)
    unknown = pd.read_csv(unknown_path)
    if len(predictions) != query_count * candidate_count:
        raise ValueError(f"incomplete predictions in {library_dir}")
    if len(unknown) != query_count:
        raise ValueError(f"incomplete unknown table in {library_dir}")
    scores = dict(
        zip(
            zip(predictions["query_id"], predictions["phase_id"], strict=True),
            predictions["score"],
            strict=True,
        )
    )
    unknown_scores = dict(
        zip(unknown["query_id"], unknown["unknown_score"], strict=True)
    )
    if not np.isfinite(list(unknown_scores.values())).all():
        raise ValueError(f"non-finite unknown score in {library_dir}")
    hashes = {
        "predictions_sha256": sha256(prediction_path),
        "sets_sha256": sha256(set_path),
        "unknown_sha256": sha256(unknown_path),
    }
    return scores, unknown_scores, hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--queries-file", type=Path)
    parser.add_argument("--spectra-dir", type=Path)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--julia", type=Path, required=True)
    parser.add_argument("--julia-project", type=Path, required=True)
    parser.add_argument("--julia-depot", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args()

    manifest = json.loads(
        (args.cases / "manifest.json").read_text(encoding="utf-8")
    )
    source_id = manifest.get("source_id", DEFAULT_SOURCE_ID)
    query_file = args.queries_file or args.dataset / "public" / "queries.csv"
    queries = pd.read_csv(
        query_file,
        dtype={"query_id": str},
    )
    spectra_dir = args.spectra_dir or (
        args.dataset / Path(queries.iloc[0]["spectrum_file"]).parent
    )
    candidates = pd.read_csv(
        args.cases / "candidate_structures.csv",
        dtype=str,
    ).sort_values("phase_id")
    phase_ids = candidates["phase_id"].tolist()
    if len(phase_ids) != 20:
        raise ValueError("expected 20 candidate families")
    args.outdir.mkdir(parents=True, exist_ok=True)

    environment = os.environ.copy()
    environment["JULIA_DEPOT_PATH"] = str(args.julia_depot)
    environment["JULIA_NUM_THREADS"] = str(
        max(1, min(4, (os.cpu_count() or 1) // max(1, args.workers)))
    )

    def run_one(library: dict) -> dict:
        library_id = library["library_id"]
        library_dir = args.outdir / library_id
        expected_candidates = library["candidate_count"]
        if library_dir.exists():
            scores, unknown, hashes = read_outputs(
                library_dir,
                len(queries),
                expected_candidates,
            )
            print(f"reused {library_id}", flush=True)
            return {
                "library_id": library_id,
                "scores": scores,
                "unknown": unknown,
                "hashes": hashes,
                "seconds": None,
            }

        library_dir.mkdir()
        command = [
            str(args.julia),
            f"--project={args.julia_project}",
            str(args.runner),
            f"--sticks={args.dataset / 'public' / 'candidate_sticks.csv'}",
            f"--queries={query_file}",
            f"--spectra-dir={spectra_dir}",
            f"--candidates={args.cases / 'candidate_structures.csv'}",
            f"--candidate-ids={','.join(library['candidate_ids'])}",
            f"--out={library_dir / 'predictions.csv'}",
            f"--sets={library_dir / 'sets.csv'}",
            f"--unknown-out={library_dir / 'query_unknown.csv'}",
            f"--max-queries={len(queries)}",
            f"--max-depth={args.max_depth}",
        ]
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=args.julia_project,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3600,
            check=False,
        )
        seconds = round(time.perf_counter() - started, 3)
        (library_dir / "stdout.log").write_text(
            completed.stdout,
            encoding="utf-8",
        )
        (library_dir / "stderr.log").write_text(
            completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"CrystalShift failed for {library_id}: "
                f"{completed.stderr[-2000:]}"
            )
        scores, unknown, hashes = read_outputs(
            library_dir,
            len(queries),
            expected_candidates,
        )
        print(f"completed {library_id} in {seconds} seconds", flush=True)
        return {
            "library_id": library_id,
            "scores": scores,
            "unknown": unknown,
            "hashes": hashes,
            "seconds": seconds,
        }

    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, library): library["library_id"]
            for library in manifest["libraries"]
        }
        try:
            for future in as_completed(futures):
                result = future.result()
                results[result["library_id"]] = result
        except Exception:
            for future in futures:
                future.cancel()
            raise

    score_by_library = {
        key: value["scores"] for key, value in results.items()
    }
    unknown_by_library = {
        key: value["unknown"] for key, value in results.items()
    }
    timings = {
        key: value["seconds"] for key, value in results.items()
    }
    output_hashes = {
        key: value["hashes"] for key, value in results.items()
    }

    cases = pd.read_csv(args.cases / "cases.csv", dtype=str).fillna("")
    truth = pd.read_csv(
        args.cases / "case_phase_truth.csv",
        dtype={"case_id": str, "phase_id": str, "present": int},
    )
    full_scores = score_by_library["full"]
    full_unknown = unknown_by_library["full"]
    candidate_rows = []
    fixed_candidate_rows = []
    case_rows = []
    fixed_case_rows = []
    for case in cases.itertuples(index=False):
        library_id = (
            "full"
            if case.condition == "closed"
            else f"minus_{case.omitted_phase_id}"
        )
        available = sorted(
            truth.loc[truth["case_id"].eq(case.case_id), "phase_id"].tolist()
        )
        if len(available) != int(case.candidate_count):
            raise ValueError(f"{case.case_id}: candidate count mismatch")
        for phase_id in available:
            candidate_rows.append(
                {
                    "case_id": case.case_id,
                    "phase_id": phase_id,
                    "score": float(
                        score_by_library[library_id][(case.query_id, phase_id)]
                    ),
                }
            )
            fixed_candidate_rows.append(
                {
                    "case_id": case.case_id,
                    "phase_id": phase_id,
                    "score": float(full_scores[(case.query_id, phase_id)]),
                }
            )
        case_rows.append(
            {
                "case_id": case.case_id,
                "unknown_score": float(
                    unknown_by_library[library_id][case.query_id]
                ),
            }
        )
        fixed_case_rows.append(
            {
                "case_id": case.case_id,
                "unknown_score": float(full_unknown[case.query_id]),
            }
        )

    tables = {
        "candidate_predictions.csv": candidate_rows,
        "case_scores.csv": case_rows,
        "fixed_output_candidate_predictions.csv": fixed_candidate_rows,
        "fixed_output_case_scores.csv": fixed_case_rows,
    }
    for name, rows in tables.items():
        frame = pd.DataFrame(rows)
        sort_columns = ["case_id", "phase_id"] if "phase_id" in frame else ["case_id"]
        frame.sort_values(sort_columns).to_csv(
            args.outdir / name,
            index=False,
            lineterminator="\n",
        )
    if len(candidate_rows) != len(truth) or len(case_rows) != len(cases):
        raise ValueError("unexpected completed submission size")

    status = {
        "status": f"{source_id}_crystalshift_panel_complete",
        "method": "CrystalShift.jl",
        "source": source_id,
        "source_commit": "c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8",
        "julia_version": "1.10.13",
        "julia_threads": environment["JULIA_NUM_THREADS"],
        "parallel_workers": args.workers,
        "max_depth": args.max_depth,
        "libraries": len(manifest["libraries"]),
        "queries": len(queries),
        "cases": len(case_rows),
        "candidate_truth_rows": len(candidate_rows),
        "seconds_per_library": timings,
        "candidate_predictions_sha256": sha256(
            args.outdir / "candidate_predictions.csv"
        ),
        "case_scores_sha256": sha256(args.outdir / "case_scores.csv"),
        "fixed_output_candidate_predictions_sha256": sha256(
            args.outdir / "fixed_output_candidate_predictions.csv"
        ),
        "fixed_output_case_scores_sha256": sha256(
            args.outdir / "fixed_output_case_scores.csv"
        ),
        "library_output_hashes": output_hashes,
        "unknown_score": (
            "normalized squared residual of the highest-probability "
            "CrystalShift phase-set node"
        ),
    }
    (args.outdir / "execution_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
