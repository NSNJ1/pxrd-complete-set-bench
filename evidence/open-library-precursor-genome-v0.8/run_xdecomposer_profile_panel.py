#!/usr/bin/env python3
"""Run official XDecomposer against frozen Precursor Genome profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RELEASE_ROOT = Path(
    os.environ.get(
        "XDECOMPOSER_RELEASE_ROOT",
        "external_methods_xdecomposer_20261125/release_source_V_0.0.1",
    )
)
CHECKPOINT_ROOT = Path(
    os.environ.get(
        "XDECOMPOSER_CHECKPOINT_ROOT",
        "external_methods_xdecomposer_20261125/official_checkpoints",
    )
)
CU_GRID = np.linspace(10.0, 80.0, 3500, dtype=np.float64)
FWHM = 0.10
SEED = 20261127

if str(RELEASE_ROOT) not in sys.path:
    sys.path.insert(0, str(RELEASE_ROOT))

from src.models.hybrid_film import build_hybrid_model
from src.models.xrd_transformer import XRDMaskedAutoencoder


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_model(device: torch.device):
    separation = torch.load(
        CHECKPOINT_ROOT / "separation_latest.pt",
        map_location="cpu",
        weights_only=False,
    )
    pretrain = torch.load(
        CHECKPOINT_ROOT / "pretrain_checkpoint_latest.pt",
        map_location="cpu",
        weights_only=False,
    )
    separation_config = separation["config"]
    pretrain_config = pretrain.get("config", {})
    mae = XRDMaskedAutoencoder(
        xrd_length=separation_config["xrd_length"],
        d_model=pretrain_config.get("d_model", 768),
        n_layers=pretrain_config.get("n_layers", 4),
        n_heads=pretrain_config.get("n_heads", 12),
        decoder_d_model=pretrain_config.get("decoder_dim", 512),
        decoder_n_layers=pretrain_config.get("decoder_layers", 4),
    )
    model = build_hybrid_model(
        mae,
        num_sources=separation_config["num_phases"],
        cnn_channels=separation_config.get(
            "cnn_channels",
            [64, 128, 256, 512],
        ),
        cnn_kernels=separation_config.get("cnn_kernels"),
        cnn_strides=separation_config.get("cnn_strides"),
    )
    state_dict = {
        key.removeprefix("module."): value
        for key, value in separation["model_state_dict"].items()
    }
    model.load_state_dict(state_dict)
    return model.to(device).eval()


def load_reference(path: Path) -> np.ndarray:
    frame = pd.read_csv(path)
    values = np.interp(
        CU_GRID,
        frame["two_theta"].to_numpy(dtype=float),
        frame["intensity"].to_numpy(dtype=float),
        left=0.0,
        right=0.0,
    )
    values = np.clip(values, 0.0, None)
    maximum = float(values.max())
    if maximum <= 0:
        raise ValueError(f"empty reference: {path}")
    return values / maximum


def load_measurement(path: Path) -> np.ndarray:
    frame = np.loadtxt(path)
    values = np.interp(
        CU_GRID,
        frame[:, 0].astype(float),
        np.clip(frame[:, 1].astype(float), 0.0, None),
        left=0.0,
        right=0.0,
    )
    maximum = float(values.max())
    if maximum <= 0:
        raise ValueError(f"empty measurement: {path}")
    return values / maximum


def centered_unit_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    values = values - values.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.clip(norms, 1e-15, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    candidates = pd.read_csv(
        args.dataset / "public" / "candidates.csv",
        dtype=str,
    ).sort_values("candidate_id")
    phase_ids = candidates["candidate_id"].tolist()
    if len(phase_ids) != 20:
        raise ValueError("expected 20 candidates")
    queries = pd.read_csv(
        args.dataset / "public" / "queries.csv",
        dtype={"query_id": str},
    )
    cases = pd.read_csv(args.cases / "cases.csv", dtype=str).fillna("")
    truth = pd.read_csv(
        args.cases / "case_phase_truth.csv",
        dtype={"case_id": str, "phase_id": str, "present": int},
    )
    reference_matrix = centered_unit_rows(
        np.vstack(
            [
                load_reference(args.dataset / row.reference_profile_file)
                for row in candidates.itertuples(index=False)
            ]
        )
    )
    model = load_model(device)

    records = {}
    for row in queries.itertuples(index=False):
        measurement = load_measurement(args.dataset / row.spectrum_file)
        tensor = torch.as_tensor(
            measurement,
            dtype=torch.float32,
            device=device,
        ).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            components, activity_logits = model(tensor)
        component_values = components[0].detach().cpu().numpy().astype(
            np.float64
        )
        activity = torch.sigmoid(activity_logits)[0].detach().cpu().numpy()
        correlations = np.clip(
            centered_unit_rows(component_values) @ reference_matrix.T,
            0.0,
            1.0,
        )
        scores = np.max(activity[:, None] * correlations, axis=0)
        records[str(row.query_id)] = {
            "activity": activity,
            "correlations": correlations,
            "scores": scores,
        }

    candidate_index = {
        phase_id: index for index, phase_id in enumerate(phase_ids)
    }
    candidate_rows = []
    fixed_candidate_rows = []
    case_rows = []
    fixed_case_rows = []
    for case in cases.itertuples(index=False):
        record = records[str(case.query_id)]
        available = truth.loc[
            truth["case_id"].eq(case.case_id),
            "phase_id",
        ].tolist()
        if len(available) != int(case.candidate_count):
            raise ValueError(f"{case.case_id}: candidate count mismatch")
        available_indices = [candidate_index[item] for item in available]
        full_unknown = float(
            np.max(record["activity"] * (1.0 - record["correlations"].max(axis=1)))
        )
        best_available = np.max(
            record["correlations"][:, available_indices],
            axis=1,
        )
        actual_unknown = float(
            np.max(record["activity"] * (1.0 - best_available))
        )
        for phase_id in available:
            score = float(record["scores"][candidate_index[phase_id]])
            candidate_rows.append(
                {
                    "case_id": case.case_id,
                    "phase_id": phase_id,
                    "score": score,
                }
            )
            fixed_candidate_rows.append(
                {
                    "case_id": case.case_id,
                    "phase_id": phase_id,
                    "score": score,
                }
            )
        case_rows.append(
            {
                "case_id": case.case_id,
                "unknown_score": actual_unknown,
            }
        )
        fixed_case_rows.append(
            {
                "case_id": case.case_id,
                "unknown_score": full_unknown,
            }
        )

    args.outdir.mkdir(parents=True, exist_ok=False)
    outputs = {
        "candidate_predictions.csv": candidate_rows,
        "case_scores.csv": case_rows,
        "fixed_output_candidate_predictions.csv": fixed_candidate_rows,
        "fixed_output_case_scores.csv": fixed_case_rows,
    }
    for name, rows in outputs.items():
        frame = pd.DataFrame(rows)
        columns = ["case_id", "phase_id"] if "phase_id" in frame else ["case_id"]
        frame.sort_values(columns).to_csv(
            args.outdir / name,
            index=False,
            lineterminator="\n",
        )

    status = {
        "status": "precursor_genome_xdecomposer_profile_panel_complete",
        "method": "XDecomposer official V_0.0.1",
        "source": "precursor_genome",
        "queries": len(queries),
        "cases": len(case_rows),
        "candidate_rows": len(candidate_rows),
        "device": str(device),
        "candidate_predictions_sha256": sha256(
            args.outdir / "candidate_predictions.csv"
        ),
        "case_scores_sha256": sha256(args.outdir / "case_scores.csv"),
        "claim_boundary": (
            "Official model components correlate against source-derived "
            "reference profiles from reactions excluded from the query set."
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
