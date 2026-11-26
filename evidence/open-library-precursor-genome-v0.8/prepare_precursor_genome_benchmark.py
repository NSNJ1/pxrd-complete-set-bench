#!/usr/bin/env python3
"""Build the frozen 20-candidate Precursor Genome measured benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pickle
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zip_range_reader import read_member

RAW_SCANS_URL = (
    "https://zenodo.org/api/records/21285546/files/raw_scans.zip/content"
)
REFINEMENT_PKLS_URL = (
    "https://zenodo.org/api/records/21285546/files/refinement_pkls.zip/content"
)
COMMON_GRID = np.arange(10.0, 100.0001, 0.02)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def phase_identity(phase_id: str) -> tuple[str, int, str]:
    match = re.fullmatch(
        r"(.+)_([0-9]{1,3})_\(icsd_([0-9]+)\)(?:-[A-Za-z0-9]+)?",
        phase_id,
    )
    if match is None:
        raise ValueError(f"unexpected phase identifier: {phase_id!r}")
    formula, spacegroup, icsd_id = match.groups()
    return formula, int(spacegroup), icsd_id


def candidate_id_from_phase(phase_id: str) -> str:
    formula, spacegroup, icsd_id = phase_identity(phase_id)
    clean_formula = re.sub(r"[^A-Za-z0-9]+", "", formula)
    return f"{clean_formula}_sg{spacegroup}_icsd{icsd_id}".lower()


def crystal_system(spacegroup: int) -> str:
    if 1 <= spacegroup <= 2:
        return "triclinic"
    if 3 <= spacegroup <= 15:
        return "monoclinic"
    if 16 <= spacegroup <= 74:
        return "orthorhombic"
    if 75 <= spacegroup <= 142:
        return "tetragonal"
    if 143 <= spacegroup <= 167:
        return "trigonal"
    if 168 <= spacegroup <= 194:
        return "hexagonal"
    if 195 <= spacegroup <= 230:
        return "cubic"
    raise ValueError(f"invalid space group: {spacegroup}")


def safe_unpickle(data: bytes) -> dict:
    class SafeUnpickler(pickle.Unpickler):
        def find_class(self, module: str, name: str) -> object:
            raise pickle.UnpicklingError(
                f"executable global is not allowed: {module}.{name}"
            )

    value = SafeUnpickler(io.BytesIO(data)).load()
    if not isinstance(value, dict):
        raise TypeError("refinement pickle root is not a dictionary")
    return value


def read_remote_member(
    url: str,
    member: str,
    attempts: int = 4,
) -> bytes:
    return read_member(url, member, attempts=attempts)


def read_cached_member(
    url: str,
    member: str,
    cache_dir: Path,
) -> bytes:
    cache_dir.mkdir(parents=True, exist_ok=True)
    suffix = PurePosixPath(member).suffix or ".bin"
    key = hashlib.sha256(f"{url}|{member}".encode()).hexdigest()
    cache_path = cache_dir / f"{key}{suffix}"
    if cache_path.exists():
        return cache_path.read_bytes()
    value = read_remote_member(url, member)
    cache_path.write_bytes(value)
    return value


def lattice_values(
    raw_lattice: dict,
    spacegroup: int,
) -> tuple[float, float, float, float, float, float]:
    def value(name: str) -> float | None:
        item = raw_lattice.get(name)
        if item is None:
            return None
        if isinstance(item, (list, tuple)):
            item = item[0]
        return float(item) * 10.0

    system = crystal_system(spacegroup)
    a = value("a")
    b = value("b")
    c = value("c")
    alpha = (
        float(raw_lattice["alpha"][0])
        if raw_lattice.get("alpha") is not None
        else None
    )
    beta = (
        float(raw_lattice["beta"][0])
        if raw_lattice.get("beta") is not None
        else None
    )
    gamma = (
        float(raw_lattice["gamma"][0])
        if raw_lattice.get("gamma") is not None
        else None
    )
    if a is None:
        raise ValueError("missing lattice a")
    if system == "cubic":
        b, c = a, a
        alpha = beta = gamma = 90.0
    elif system == "tetragonal":
        b = a
        alpha = beta = gamma = 90.0
    elif system == "orthorhombic":
        alpha = beta = gamma = 90.0
    elif system in {"hexagonal", "trigonal"} and b is None:
        b = a
        alpha = beta = 90.0
        gamma = 120.0
    elif system == "monoclinic":
        alpha = gamma = 90.0
    if None in (b, c, alpha, beta, gamma):
        raise ValueError(
            f"incomplete lattice for space group {spacegroup}: {raw_lattice}"
        )
    return (
        float(a),
        float(b),
        float(c),
        float(alpha),
        float(beta),
        float(gamma),
    )


def phase_peaks(
    refinement: dict,
    phase_id: str,
) -> pd.DataFrame:
    peak_data = refinement["peak_data"]
    length = len(peak_data["2theta"])
    rows = []
    for index in range(length):
        if peak_data["phase"][str(index)] != phase_id:
            continue
        angle = float(peak_data["2theta"][str(index)])
        intensity = float(peak_data["intensity"][str(index)])
        if not np.isfinite(angle) or not np.isfinite(intensity):
            continue
        if intensity <= 0.0:
            continue
        rows.append(
            {
                "h": round(float(peak_data["h"][str(index)])),
                "k": round(float(peak_data["k"][str(index)])),
                "l": round(float(peak_data["l"][str(index)])),
                "two_theta": angle,
                "intensity": intensity,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"no peaks for {phase_id}")
    frame["intensity"] /= frame["intensity"].max()
    return frame.sort_values(["two_theta", "h", "k", "l"])


def profile_from_refinement(
    refinement: dict,
    phase_id: str,
) -> pd.DataFrame:
    plot = refinement["plot_data"]
    angles = np.asarray(plot["x"], dtype=float)
    intensity = np.asarray(plot["structs"][phase_id], dtype=float)
    if len(angles) != len(intensity):
        raise ValueError("phase profile length mismatch")
    order = np.argsort(angles)
    angles = angles[order]
    intensity = intensity[order]
    values = np.interp(
        COMMON_GRID,
        angles,
        intensity,
        left=0.0,
        right=0.0,
    )
    values = np.clip(values, 0.0, None)
    maximum = float(values.max())
    if not np.isfinite(maximum) or maximum <= 0.0:
        raise ValueError(f"empty phase profile: {phase_id}")
    return pd.DataFrame(
        {
            "two_theta": COMMON_GRID,
            "intensity": values / maximum,
        }
    )


def read_xrdml_bytes(data: bytes) -> tuple[np.ndarray, np.ndarray]:
    root = ET.fromstring(data)
    elements = {}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        elements.setdefault(tag, element)
    counts = elements.get("counts")
    start = elements.get("startPosition")
    stop = elements.get("endPosition")
    wavelength = elements.get("kAlpha1")
    if any(item is None for item in (counts, start, stop, wavelength)):
        raise ValueError("incomplete XRDML record")
    intensity = np.fromstring(counts.text or "", sep=" ")
    two_theta = np.linspace(
        float(start.text),
        float(stop.text),
        len(intensity),
    )
    if len(two_theta) < 100:
        raise ValueError("too few XRDML points")
    if not np.isfinite(intensity).all() or intensity.min() < 0:
        raise ValueError("invalid XRDML intensity")
    if abs(float(wavelength.text) - 1.540598) > 1e-5:
        raise ValueError(f"unexpected wavelength: {wavelength.text}")
    return two_theta, intensity.astype(float)


def write_spectrum(path: Path, angles: np.ndarray, intensity: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=" ", lineterminator="\n")
        writer.writerows(
            (f"{angle:.10f}", f"{value:.10f}")
            for angle, value in zip(angles, intensity, strict=True)
        )


def write_sticks(
    path: Path,
    candidate_records: list[dict],
    peak_frames: dict[str, pd.DataFrame],
) -> None:
    blocks = []
    for index, record in enumerate(candidate_records):
        lattice = record["lattice"]
        header = ",".join(
            [
                str(index),
                candidate_id_from_phase(record["phase_id"]),
                record["crystal_system"],
                f"{lattice[0]:.6f}",
                f"{lattice[1]:.6f}",
                f"{lattice[2]:.6f}",
                f"{lattice[3]:.6f}",
                f"{lattice[4]:.6f}",
                f"{lattice[5]:.6f}",
            ]
        )
        lines = [header]
        for row in peak_frames[record["phase_id"]].itertuples(index=False):
            lines.append(
                f"{row.h},{row.k},{row.l},"
                f"{row.two_theta:.10f},{row.intensity:.10f}"
            )
        blocks.append("\n".join(lines))
    path.write_text("\n#\n".join(blocks) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=False)
    ledger_path = args.ledger.resolve()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    samples = {sample["sample_id"]: sample for sample in ledger["samples"]}
    selection_manifest = json.loads(
        (args.selection / "SELECTION_MANIFEST.json").read_text(encoding="utf-8")
    )
    if selection_manifest.get("status") != "precursor_genome_selection_frozen":
        raise ValueError("selection manifest is not frozen")
    references = pd.read_csv(
        args.selection / "reference_manifest.csv",
        dtype={"phase_id": str, "reference_sample_id": str},
    )
    queries = pd.read_csv(
        args.selection / "query_manifest.csv",
        dtype={"sample_id": str},
    )
    cache_dir = args.cache_dir or (args.outdir.parent / "remote_member_cache")

    candidate_records = []
    peak_frames = {}
    profile_frames = {}
    for row in references.itertuples(index=False):
        pkl_member = str(row.reference_pkl_member)
        print(f"reading reference {row.phase_id}: {pkl_member}", flush=True)
        pkl_bytes = read_cached_member(
            REFINEMENT_PKLS_URL,
            pkl_member,
            cache_dir / "pkl",
        )
        refinement = safe_unpickle(pkl_bytes)
        phase_id = str(row.phase_id)
        if phase_id not in refinement["phase_weights"]:
            raise ValueError(f"{phase_id} absent from reference pickle")
        formula, spacegroup, icsd_id = phase_identity(phase_id)
        candidate_id = candidate_id_from_phase(phase_id)
        candidate_records.append(
            {
                "candidate_id": candidate_id,
                "phase_id": phase_id,
                "formula": formula,
                "spacegroup_number": spacegroup,
                "icsd_id": icsd_id,
                "crystal_system": crystal_system(spacegroup),
                "reference_sample_id": str(row.reference_sample_id),
                "reference_phase_weight": float(row.reference_phase_weight),
                "reference_pkl_member": pkl_member,
                "reference_pkl_sha256": hashlib.sha256(pkl_bytes).hexdigest(),
                "pkl_rwp": float(refinement["best_rwp"]),
                "lattice": list(
                    lattice_values(refinement["lattice_params"][phase_id], spacegroup)
                ),
            }
        )
        peak_frames[phase_id] = phase_peaks(refinement, phase_id)
        profile_frames[phase_id] = profile_from_refinement(
            refinement,
            phase_id,
        )

    if len(candidate_records) != 20:
        raise ValueError("expected 20 candidate records")
    if len({record["candidate_id"] for record in candidate_records}) != 20:
        raise ValueError("candidate IDs are not unique")
    candidate_records.sort(key=lambda record: record["candidate_id"])

    public = args.outdir / "public"
    evaluator = args.outdir / "evaluator"
    (public / "spectra").mkdir(parents=True)
    (public / "reference_profiles").mkdir()
    evaluator.mkdir()

    candidate_rows = []
    for record in candidate_records:
        profile_path = (
            public
            / "reference_profiles"
            / f"{record['candidate_id']}.csv"
        )
        profile_frames[record["phase_id"]].to_csv(
            profile_path,
            index=False,
            lineterminator="\n",
            float_format="%.10f",
        )
        candidate_rows.append(
            {
                "candidate_id": record["candidate_id"],
                "reference_profile_file": (
                    f"public/reference_profiles/{record['candidate_id']}.csv"
                ),
                "reference_profile_sha256": sha256(profile_path),
            }
        )
    pd.DataFrame(candidate_rows).to_csv(
        public / "candidates.csv",
        index=False,
        lineterminator="\n",
    )
    write_sticks(
        public / "candidate_sticks.csv",
        candidate_records,
        peak_frames,
    )

    query_rows = []
    truth_rows = []
    query_phase_sets = {}
    for row in queries.sort_values("sample_id").itertuples(index=False):
        sample_id = str(row.sample_id)
        if sample_id not in samples:
            raise ValueError(f"unknown query sample: {sample_id}")
        phase_weights = json.loads(row.phase_weights_json)
        phase_to_candidate = {
            record["phase_id"]: record["candidate_id"]
            for record in candidate_records
        }
        missing = sorted(set(phase_weights) - set(phase_to_candidate))
        if missing:
            raise ValueError(f"{sample_id}: missing phase candidates {missing}")
        raw_member = str(row.scan_archive_member)
        raw_bytes = read_cached_member(
            RAW_SCANS_URL,
            raw_member,
            cache_dir / "raw",
        )
        angles, intensity = read_xrdml_bytes(raw_bytes)
        spectrum_file = f"public/spectra/{sample_id}.csv"
        write_spectrum(args.outdir / spectrum_file, angles, intensity)
        query_rows.append(
            {
                "query_id": sample_id,
                "cluster_id": sample_id,
                "spectrum_file": spectrum_file,
                "quality_score": int(row.quality_score),
                "phase_count": len(phase_weights),
                "wavelength_angstrom": f"{1.5405980:.7f}",
                "scan_archive_member": raw_member,
                "scan_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
        present_candidates = {
            phase_to_candidate[phase_id] for phase_id in phase_weights
        }
        query_phase_sets[sample_id] = present_candidates
        for candidate in candidate_rows:
            truth_rows.append(
                {
                    "query_id": sample_id,
                    "phase_id": candidate["candidate_id"],
                    "present": int(
                        candidate["candidate_id"] in present_candidates
                    ),
                }
            )

    pd.DataFrame(query_rows)[
        [
            "query_id",
            "cluster_id",
            "spectrum_file",
            "wavelength_angstrom",
        ]
    ].to_csv(
        public / "queries.csv",
        index=False,
        lineterminator="\n",
    )
    pd.DataFrame(query_rows)[
        [
            "query_id",
            "cluster_id",
            "quality_score",
            "phase_count",
            "scan_archive_member",
            "scan_sha256",
        ]
    ].to_csv(
        evaluator / "query_metadata.csv",
        index=False,
        lineterminator="\n",
    )
    pd.DataFrame(truth_rows).to_csv(
        evaluator / "truth.csv",
        index=False,
        lineterminator="\n",
    )
    pd.DataFrame(candidate_records).to_csv(
        evaluator / "candidate_source_provenance.csv",
        index=False,
        lineterminator="\n",
    )

    manifest = {
        "status": "precursor_genome_benchmark_prepared",
        "source": {
            "record": "21285546",
            "doi": "10.5281/zenodo.21285546",
            "license": "CC BY 4.0",
            "ledger_sha256": sha256(ledger_path),
            "raw_scans_archive_member_size": 23008523,
            "raw_scans_archive_member_md5": "e22405e733fc79ff4b14b679f87a33d5",
            "refinement_pkl_archive_member_size": 291408941,
            "refinement_pkl_archive_member_md5": "49447823b4e017524fd963ec3734af74",
        },
        "queries": len(query_rows),
        "clusters": len({row["cluster_id"] for row in query_rows}),
        "candidate_families": len(candidate_rows),
        "truth_rows": len(truth_rows),
        "phase_count_distribution": dict(
            sorted(Counter(row["phase_count"] for row in query_rows).items())
        ),
        "quality_distribution": dict(
            sorted(Counter(row["quality_score"] for row in query_rows).items())
        ),
        "candidate_manifest_sha256": sha256(public / "candidates.csv"),
        "candidate_sticks_sha256": sha256(public / "candidate_sticks.csv"),
        "query_manifest_sha256": sha256(public / "queries.csv"),
        "query_metadata_sha256": sha256(
            evaluator / "query_metadata.csv"
        ),
        "truth_sha256": sha256(evaluator / "truth.csv"),
        "claim_boundary": (
            "Previously unused external measured retrospective holdout. "
            "Candidate reference profiles come from reference reactions excluded "
            "from the query set; one active scan per physical reaction."
        ),
        "selection_manifest_sha256": sha256(
            args.selection / "SELECTION_MANIFEST.json"
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
