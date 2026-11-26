# Precursor Genome active progress

Updated: 2026-11-27

## Frozen source

- Zenodo record: `10.5281/zenodo.21285546`, version 1.0, CC BY 4.0;
- 1,035 A-Lab reactions; 1,351 scans; 1,950 refinement cases;
- 102 independent query reactions after selecting a covered top-20 phase
  library and excluding all 20 reference reactions;
- 92 two-phase and 10 three-phase queries;
- 80 quality-1 and 22 quality-2 queries;
- 418 cases: 102 closed, 214 true omissions and 102 absent omissions;
- 8,044 case-phase truth rows.

This source was used in the project's earlier closed-library benchmark. The
open-library panel is a new intervention on a consumed source, not a fresh
external holdout: 77/102 query IDs overlap the earlier cohort and 25 are new.

## Final data lineage

- `dataset_v7` is the authoritative dataset.
- Public `queries.csv` contains only query ID, cluster ID, spectrum path and
  wavelength.
- Source-derived quality and phase count moved to
  `evaluator/query_metadata.csv`.
- `cases_v8` is the authoritative case set and uses
  `reference_profile_file`, not the legacy `cif_file`, header.
- Relative to `dataset_v6`, only the public query table, evaluator metadata and
  manifest changed. Candidate profiles, sticks, spectra and truth are
  byte-identical.
- Relative to `cases_v7`, only the candidate table header changed. Cases,
  case truth, provenance and the library manifest are byte-identical.

## Completed method outputs

- `profile_baseline_run_v8`: 102 queries, 418 cases, 8,044 candidate rows;
- `xdecomposer_run_v8`: 102 queries, 418 cases, 8,044 candidate rows;
- final `crystalshift_run_v8`: complete for all 21 libraries.

The repeat hashes for profile correlation and XDecomposer are byte-identical
to their earlier runs. CrystalShift completed all 21 libraries twice; all 63
lower-level prediction, set-probability and unknown-score files were
byte-identical, as were the four assembled tables.

## Corrected ranking denominator

An audit found that the old rank summary mixed absent-candidate controls into
the retained-true-order denominator. The corrected rule uses only
`omit_present` cases that retain at least two true candidates.

- Algarve eligible cases: 9; XMatcher 0/9, CrystalShift 2/9;
- Dara eligible cases: 30; XMatcher 0/30, CrystalShift 15/30,
  XDecomposer 0/30.

The unknown-evidence endpoint was unaffected. Corrected score summaries:

- Algarve:
  `polen_sdlm4e_algarve_chert_20261126/scores/condition_audit_20261127/`;
- Dara:
  `dara_second_source_20261126/scores_condition_audit_20261127/`;
- Dara two-minute sensitivity:
  `dara_second_source_20261126/scores_sensitivity_condition_audit_20261127/`.

## Completed analysis

- `scores_v8/summary.json`: primary 10,000-replicate score;
- `sensitivity_v8/summary.json`: frozen sensitivities;
- `RELEASE_AUDIT_20261127.json`: local release audit;
- `PRECURSOR_GENOME_RESULTS_20261127_zh.md`: report;
- `README.md`: reproduction guide.

Primary unknown-evidence differences:

| Method | Actual | Reused | Difference | 95% CI |
| --- | ---: | ---: | ---: | --- |
| shifted Pearson control | 0.7082 | 0.5071 | +0.2011 | `[0.1848, 0.2167]` |
| CrystalShift | 0.8044 | 0.5024 | +0.3019 | `[0.2737, 0.3318]` |
| XDecomposer | 0.5633 | 0.5061 | +0.0571 | `[0.0329, 0.0839]` |

The reported local audit passed 9,855 checks. Its SHA-256 is
`bbae068e9f54c33a783b20fd77097a90e17a61f0cce6ad96b9fbab90519e4215`.

## Remaining external gate

The open-library release still needs an execution by a person who did not
participate in implementation. The local benchmark cannot self-certify that
external step. No additional candidate-library calibration is planned on this
source.
