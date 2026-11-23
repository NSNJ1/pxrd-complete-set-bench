"""Run the frozen four-candidate panel through a local XMatcher API."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

PHASES = ("A", "B", "C", "D")
MO_KALPHA = 0.70932
CU_KALPHA = 1.5406


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mo_to_cu_two_theta(two_theta_mo: np.ndarray) -> np.ndarray:
    theta_mo = np.radians(two_theta_mo / 2.0)
    argument = (CU_KALPHA / MO_KALPHA) * np.sin(theta_mo)
    if np.any(argument > 1.0):
        raise ValueError("Mo K-alpha angle cannot be converted to Cu K-alpha")
    return 2.0 * np.degrees(np.arcsin(argument))


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if len(manifest.get("candidates", [])) != 4:
        raise ValueError("XMatcher panel requires exactly four candidates")
    if len(manifest.get("spectra", [])) != 25:
        raise ValueError("XMatcher panel requires exactly 25 spectra")
    return manifest


def candidate_root(manifest_path: Path, manifest: dict) -> Path:
    first_path = manifest["spectra"][0]["path"]
    if first_path.startswith("input/"):
        return manifest_path.parent.parent
    return manifest_path.parent


def verify_inputs(root: Path, manifest: dict) -> list[dict]:
    records = manifest["candidates"] + manifest["spectra"]
    verified = []
    for record in records:
        path = root / record["path"]
        observed = sha256(path)
        if observed != record["sha256"]:
            raise ValueError(f"input hash mismatch: {path}")
        verified.append(
            {
                "path": record["path"],
                "sha256": observed,
            }
        )
    return verified


def default_params() -> dict:
    return {
        "min_peak_height": 3.0,
        "min_peak_prominence": 2.0,
        "min_peak_distance": 0.1,
        "smooth_window": 7,
        "baseline_window_fraction": 0.05,
        "n_peaks": 4,
        "position_tolerance": 0.2,
        "intensity_weight": 0.15,
        "position_weight": 0.85,
        "min_matched_peaks": 2,
        "max_shift": 0.5,
        "shift_step": 0.02,
        "fixed_zero_shift": 0.0,
        "specimen_displacement": 0.0,
        "scoring_method": "hybrid",
        "multiphase_n_peaks": 12,
    }


def post_json(
    url: str,
    payload: dict,
    timeout: int,
    attempts: int = 3,
) -> dict:
    last_error = None
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            if result.get("status") == "error":
                raise RuntimeError(result.get("error", "XMatcher API error"))
            return result
        except (
            urllib.error.URLError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(1.0)
    raise RuntimeError(
        f"XMatcher request failed after {attempts} attempts: {last_error}"
    )


def spectrum_payload(root: Path, spectrum: dict) -> dict:
    points = np.loadtxt(root / spectrum["path"])
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f"unexpected spectrum shape: {spectrum['path']}")
    two_theta_cu = mo_to_cu_two_theta(points[:, 0])
    return {
        "two_theta": two_theta_cu.tolist(),
        "intensity": points[:, 1].tolist(),
        "params": default_params(),
        "elements": None,
        "element_filter_mode": "contains",
        "max_phases": 3,
        "candidate_pool": 4,
        "top_n": 10,
        "known_phase_elements": "",
        "known_phase_mpids": "",
    }


def phase_scores(response: dict) -> dict[str, float]:
    scores = {phase: 0.0 for phase in PHASES}
    for combination in response.get("results", []):
        for phase in combination.get("phases", []):
            phase_id = str(phase.get("cryst_id", ""))
            if phase_id not in scores:
                raise ValueError(f"unexpected phase returned by XMatcher: {phase_id!r}")
            scores[phase_id] = max(
                scores[phase_id],
                float(phase["single_phase_score"]),
            )
    return scores


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--predictions-out", type=Path, required=True)
    parser.add_argument("--raw-out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    root = candidate_root(args.manifest, manifest)
    input_hashes = verify_inputs(root, manifest)
    first_payload = spectrum_payload(root, manifest["spectra"][0])
    preflight = post_json(
        f"{args.base_url.rstrip('/')}/api/match",
        {
            "two_theta": first_payload["two_theta"],
            "intensity": first_payload["intensity"],
            "params": default_params(),
            "elements": None,
            "element_filter_mode": "contains",
            "top_n": 4,
        },
        args.timeout,
    )
    if int(preflight.get("candidate_count", -1)) != len(PHASES):
        raise RuntimeError(
            "XMatcher is not serving the frozen four-entry candidate database"
        )

    rows = []
    raw_responses = {}
    for spectrum in manifest["spectra"]:
        payload = spectrum_payload(root, spectrum)
        response = post_json(
            f"{args.base_url.rstrip('/')}/api/multiphase-match",
            payload,
            args.timeout,
        )
        raw_responses[spectrum["query_id"]] = response
        scores = phase_scores(response)
        for phase_id in PHASES:
            rows.append(
                {
                    "method_id": "xmatcher_automix",
                    "query_id": spectrum["query_id"],
                    "phase_id": phase_id,
                    "score": scores[phase_id],
                }
            )

    frame = pd.DataFrame(rows).sort_values(["query_id", "phase_id"])
    if len(frame) != 100 or frame.duplicated(["query_id", "phase_id"]).any():
        raise ValueError("XMatcher prediction grid is incomplete or duplicated")
    args.predictions_out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.predictions_out, index=False, lineterminator="\n")
    args.raw_out.write_text(
        json.dumps(
            {
                "status": "xmatcher_panel_complete",
                "method_id": "xmatcher_automix",
                "claim_boundary": (
                    "Retrospective label-blind execution on a frozen four-candidate "
                    "panel; this is not prospective validation."
                ),
                "execution": {
                    "distribution": "XMatcher Desktop 1.3.0",
                    "figshare_doi": "10.6084/m9.figshare.32812985.v7",
                    "license": "CC BY 4.0",
                    "candidate_database_entries": len(PHASES),
                    "radiation_conversion": (
                        "Mo K-alpha 0.70932 A converted to Cu K-alpha 1.5406 A "
                        "by Bragg-angle equivalence"
                    ),
                    "adaptation": (
                        "For each phase, take the maximum single_phase_score among "
                        "returned AutoMix combinations that contain the phase; an "
                        "unreturned phase receives zero. Scores are ranking evidence, "
                        "not calibrated probabilities."
                    ),
                    "request_params": default_params(),
                    "input_hashes": input_hashes,
                },
                "responses": raw_responses,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(frame)} predictions")
    print(f"predictions_sha256={sha256(args.predictions_out)}")
    print(f"raw_sha256={sha256(args.raw_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
