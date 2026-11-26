# Precursor Genome open-library panel

This directory contains the third measured source panel for
`PXRD-CompleteSetBench`. It evaluates whether full-library candidate ranking
and unknown-phase evidence remain usable when one phase family is removed from
the candidate library.

The source is the public [Precursor Genome](
https://doi.org/10.5281/zenodo.21285546) v1.0 release (CC BY 4.0). This project
already used the source in an earlier closed-library benchmark. The panel here
is a new open-library intervention on a previously consumed source, not a fresh
external or prospective cohort. There are 77/102 overlapping query IDs and 25
new queries.

## Frozen panel

- 1,035 source reactions;
- 102 independent query reactions after reference-reaction exclusion;
- 92 binary and 10 ternary reactions;
- 20 candidate phase families;
- 418 cases: 102 closed, 214 true omissions, 102 absent omissions;
- 8,044 case-phase truth rows;
- one active scan per physical reaction;
- 20 reference reactions disjoint from every query reaction.

Reference profiles are source-fitted refinement profiles, not ab initio pure
phase simulations. The source manuscript is in preparation.

The selection rules and endpoint definitions were frozen before method scores.
See `PREREGISTRATION_ADMISSION.md` and `SENSITIVITY_FREEZE_20261127.md`.

## Final data

Use:

- `dataset_v7/` as the authoritative dataset;
- `cases_v8/` as the authoritative case panel.

`dataset_v7/public/queries.csv` contains only `query_id`, `cluster_id`,
`spectrum_file` and `wavelength_angstrom`. Quality score, phase count and scan
lineage are evaluator-only in
`dataset_v7/evaluator/query_metadata.csv`.

`cases_v8/candidate_structures.csv` names reference-profile files explicitly.
The earlier `dataset_v6/` and `cases_v7/` are retained for the audit trail.
Their method-facing content is byte-identical apart from the removed public
truth columns and the corrected candidate-table header.

## Method outputs

| Directory | Method | Status |
| --- | --- | --- |
| `profile_baseline_run_v8/` | shifted Pearson correlation control | complete |
| `crystalshift_run_v8/` | CrystalShift.jl | complete |
| `xdecomposer_run_v8/` | XDecomposer V_0.0.1 | complete |

The CrystalShift panel contains one full library and 20 leave-one-family-out
libraries. A separate run produced byte-identical output for all 21 libraries
and all 63 lower-level prediction, set-probability and unknown-score files.

## Scores

- `scores_v8/summary.json`: primary 10,000-replicate cluster bootstrap;
- `sensitivity_v8/summary.json`: quality-1, unreacted and omitted-weight >= 5%
  panels.

The source is interpreted per method and endpoint. Do not pool AUROC values
across source distributions.

Primary unknown-evidence comparisons:

| Method | Actual reduced | Complete residual reused |
| --- | ---: | ---: |
| shifted Pearson control | 0.7082 | 0.5071 |
| CrystalShift | 0.8044 | 0.5024 |
| XDecomposer | 0.5633 | 0.5061 |

Only 30 true omissions retain at least two true candidates and are eligible for
the retained-true-order endpoint:

| Method | Retained-true order changed | Complete candidate order changed |
| --- | ---: | ---: |
| shifted Pearson control | 0/30 | 0/214 |
| CrystalShift | 4/30 | 174/214 |
| XDecomposer | 0/30 | 0/214 |

## Reproduction

Run from `post_abundance_shift_20261125/` after installing the declared
environment:

```powershell
python precursor_genome_source_20261127/run_profile_baseline_panel.py `
  --dataset precursor_genome_source_20261127/dataset_v7 `
  --cases precursor_genome_source_20261127/cases_v8 `
  --outdir precursor_genome_source_20261127/profile_baseline_repeat`
```

XDecomposer requires the official V_0.0.1 checkpoint and source paths defined in
`run_xdecomposer_profile_panel.py`. CrystalShift requires Julia 1.10.13,
commit `c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`, and the runner from
`external_runners/run_crystalshift_open.jl`:

```powershell
python external_runners/run_crystalshift_panel.py `
  --dataset dataset_v7 `
  --cases cases_v8 `
  --julia <path-to-julia-1.10.13/bin/julia.exe> `
  --julia-project <path-to-CrystalShift.jl> `
  --julia-depot <path-to-Julia-depot> `
  --runner external_runners/run_crystalshift_open.jl `
  --outdir crystalshift_repeat `
  --workers 3 `
  --max-depth 3
```

The exact command used for the recorded release is also documented in
`ACTIVE_PROGRESS_20261127.md`.

Score and audit:

```powershell
python precursor_genome_source_20261127/score_precursor_genome.py `
  --cases precursor_genome_source_20261127/cases_v8 `
  --profile-run precursor_genome_source_20261127/profile_baseline_run_v8 `
  --crystalshift-run precursor_genome_source_20261127/crystalshift_run_v8 `
  --xdecomposer-run precursor_genome_source_20261127/xdecomposer_run_v8 `
  --outdir precursor_genome_source_20261127/scores_v8 `
  --bootstrap-repeats 10000

python precursor_genome_source_20261127/audit_precursor_genome_release.py
```

The release audit covers source hashes, public/evaluator separation, candidate
and spectrum paths, exact case construction, library membership, method output
coverage, repeated-output identity and bootstrap completion.

## Claim boundary

The panel supports source-specific construct-validity conclusions. It does not
support a universal SOTA ranking, a prospective generalization claim, or a
claim that every method changes retained-candidate order after omission.
