"""Build a four-entry XMatcher database from the frozen candidate CIF files."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from pathlib import Path

from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.io.cif import CifParser


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pattern_entry(
    entry_id: int,
    phase_id: str,
    cif_path: Path,
    n_peaks: int,
) -> dict:
    structure = CifParser(str(cif_path)).parse_structures(primitive=False)[0]
    pattern = XRDCalculator(wavelength=1.5406).get_pattern(
        structure,
        two_theta_range=(10.0, 90.0),
        scaled=True,
    )
    strongest = sorted(
        range(len(pattern.x)),
        key=lambda index: (-float(pattern.y[index]), float(pattern.x[index])),
    )[:n_peaks]
    strongest.sort(key=lambda index: float(pattern.x[index]))

    hkls = []
    for index in strongest:
        reflections = []
        for reflection in pattern.hkls[index]:
            reflections.append(
                {
                    "hkl": [int(value) for value in reflection["hkl"]],
                    "multiplicity": int(reflection["multiplicity"]),
                }
            )
        hkls.append(reflections)

    symbol, spacegroup_number = structure.get_space_group_info()
    elements = sorted({str(element) for element in structure.composition.elements})
    return {
        "entry_id": entry_id,
        "mpid": cif_path.name,
        "formula": structure.composition.reduced_formula,
        "elements": elements,
        "n_atoms": len(structure),
        "spacegroup_number": int(spacegroup_number),
        "spacegroup_symbol": str(symbol),
        "peaks": {
            "positions": [float(pattern.x[index]) for index in strongest],
            "intensities": [float(pattern.y[index]) for index in strongest],
            "hkls": hkls,
            "d_spacings": [float(pattern.d_hkls[index]) for index in strongest],
        },
        "cryst_id": phase_id,
    }


def build_database(
    manifest_path: Path,
    n_peaks: int,
) -> tuple[dict, list[dict]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = manifest["candidates"]
    if len(candidates) != 4:
        raise ValueError("the controlled XMatcher panel requires exactly four CIFs")
    if [candidate["phase_id"] for candidate in candidates] != ["A", "B", "C", "D"]:
        raise ValueError("candidate phase identifiers must be A, B, C, and D")

    records = {}
    audit = []
    root = manifest_path.parent
    if candidates[0]["path"].startswith("input/"):
        root = manifest_path.parent.parent
    for entry_id, candidate in enumerate(candidates, start=1):
        cif_path = root / candidate["path"]
        observed_hash = sha256(cif_path)
        if observed_hash != candidate["sha256"]:
            raise ValueError(f"CIF hash mismatch for {cif_path.name}")
        record = pattern_entry(entry_id, candidate["phase_id"], cif_path, n_peaks)
        if record["formula"] != candidate["formula"]:
            raise ValueError(
                f"CIF formula mismatch for {cif_path.name}: "
                f"{record['formula']} != {candidate['formula']}"
            )
        records[entry_id] = record
        audit.append(
            {
                "entry_id": entry_id,
                "phase_id": candidate["phase_id"],
                "formula": record["formula"],
                "spacegroup_symbol": record["spacegroup_symbol"],
                "peaks": len(record["peaks"]["positions"]),
                "cif_sha256": observed_hash,
            }
        )

    element_index: dict[tuple[str, ...], list[int]] = {}
    element_inverted_index: dict[str, list[int]] = {}
    for entry_id, record in records.items():
        elements = tuple(record["elements"])
        element_index.setdefault(elements, []).append(entry_id)
        for element in elements:
            element_inverted_index.setdefault(element, []).append(entry_id)

    database = {
        "xrd_database": records,
        "element_index": element_index,
        "element_inverted_index": element_inverted_index,
        "metadata": {
            "schema_version": 2,
            "source_db": "PXRD-CompleteSetBench frozen candidates",
            "wavelength": "CuKa",
            "n_peaks": n_peaks,
            "two_theta_range": (10.0, 90.0),
            "min_d_spacing": 0.5,
            "total_entries": len(records),
            "sources": [
                {
                    "name": "PXRD-CompleteSetBench controlled candidates",
                    "entries": len(records),
                }
            ],
        },
    }
    return database, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--n-peaks", type=int, default=30)
    args = parser.parse_args()
    if args.n_peaks < 1:
        raise ValueError("--n-peaks must be positive")

    database, audit = build_database(args.manifest, args.n_peaks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("wb") as handle:
        pickle.dump(database, handle, protocol=pickle.HIGHEST_PROTOCOL)
    args.audit_out.write_text(
        json.dumps(
            {
                "status": "xmatcher_candidate_database_prepared",
                "database_sha256": sha256(args.out),
                "entries": audit,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(audit)} entries to {args.out}")
    print(f"sha256={sha256(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
