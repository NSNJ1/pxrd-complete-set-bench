# Changelog

## 0.8.0 - 2026-11-27

- Add a 102-reaction Precursor Genome open-library intervention with 20
  candidate families and 418 closed, true-omission and absent-omission cases.
- Compare actual reduced-library evidence with complete-residual reuse and an
  unavailable omitted-candidate shortcut for a profile control, CrystalShift
  and XDecomposer.
- Repeat all 21 CrystalShift library runs byte-for-byte and audit 9,855 release
  conditions.
- Prespecify quality-1, unreacted-reaction and 5%-phase-weight sensitivities.
- Record that 77 of 102 Precursor Genome query IDs were already used by the
  project's closed-library benchmark and only 25 are new; this panel is a new
  intervention, not a fresh external source.

## 0.7.0 - 2026-11-24

- Add a license-safe NASA CheMin v0.2 external benchmark with 44 measured
  patterns, 20 candidate families and 58 CC0 COD reference profiles.
- Separate the blind public handoff from the complete evaluator archive and
  verify repeated byte-identical construction.
- Add a 12-collection candidate structure/prototype overlap audit.
- Quantify candidate-structure reuse across RealBind, opXRD, RRUFF, GALAXI,
  CheMin, XCA, Ta-Sn-O and AriadneX.
- Report unavailable CSD/ICSD candidate structures instead of imputing them.

## 0.6.2 - 2026-11-24

- Add a verified fresh-release replay on DeltaXRDbench dataset v1.1.0.
- Benchmark an adapted external method on 30 RRUFF and 30 opXRD mixtures with
  20 candidate structures per query and 2-3 reference phases.
- Report a significant RRUFF/opXRD interaction for all-present@3 while the
  phase-AP disadvantage remains consistent.
- Redistribute derived metadata and results only; raw spectra and source CIFs
  remain with their original providers.

## 0.6.1 - 2026-11-24

- Add a truth-blind partial-submission scorer with explicit coverage semantics.
- Add a reproducible endpoint rank-reversal and bootstrap rank-stability audit.
- Add 20-candidate CrystalShift stress panels on RealBind and XCA Ni-Co-Al.
- Separate label-blind public handoffs from evaluator-side truth in both
  stress-panel evidence archives.
- Add exact repeat checks for both stress panels and retain their Julia warning
  logs in the published evidence.

## 0.5.0 - 2026-11-23

- Add a reproducible six-method comparison on the controlled AriadneX cohort.
- Include sanitized evidence from independent CrystalShift.jl and
  XRD-AutoAnalyzer executions.
- Report all-present tie-order bounds and make average precision explicitly
  threshold-group-aware.
- Preserve the v0.4.2 data contract and core evaluation result.

## 0.4.2 - 2026-11-20

- Reject bootstrap runs with fewer than one repeat.
- Reject dominant-phase labels attached to absent candidates.
- Allow the public-tree audit to run after users create a virtual environment.

## 0.4.1 - 2026-11-19

- Corrected package-relative reproduction commands.
- Removed developer-machine paths.
- Added a command-line evaluator and one-command core reproduction.
- Added tests for the public data and result contracts.

## 0.4.0 - 2026-11-18

- Seven measured-source cohorts and two external controls.
- Frozen 10,000-repeat cluster-bootstrap evaluation.
- Source-stratified screening and ranking diagnostics.
