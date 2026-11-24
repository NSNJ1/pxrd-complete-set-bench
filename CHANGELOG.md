# Changelog

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
