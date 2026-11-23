# PXRD-CompleteSetBench v0.5.0

This release adds a reproducible six-method comparison on the 25-query
AriadneX controlled cohort. The seven-source benchmark input and its frozen
core result are unchanged from v0.4.2.

## Method panel

The panel contains deterministic random ranking, global and eight-window
sqrt-Pearson baselines, anchored-set strict ranking, CrystalShift.jl and
XRD-AutoAnalyzer. The public table has 600 candidate scores under one fixed
four-phase candidate library.

CrystalShift.jl and XRD-AutoAnalyzer were executed from fixed upstream commits
by Minghao Li in separate environments. Sanitized evidence archives and
confirmation records are included under `evidence/external-methods/`.

## Evaluation

The panel uses threshold-group-aware average precision, fixed phase-identifier
tie breaks for the main all-present values, all-legal-order tie bounds, and
10,000 query-level bootstrap repeats with seed `20261123`.

The result separates method coverage from prospective evidence. The panel is a
retrospective control source; it is not a fresh measured cohort and does not
establish universal state of the art.

## Validation

- 20 unit and contract tests pass.
- The public-tree audit passes.
- Ruff check and format checks pass.
- The v0.4.2 core reproduction remains an exact match.
- The external panel reproduction matches canonical SHA-256
  `b39ba2b54526dbfee90863f5e25023e49f29c8c483adcc470a5d76015b14e4b5`.
