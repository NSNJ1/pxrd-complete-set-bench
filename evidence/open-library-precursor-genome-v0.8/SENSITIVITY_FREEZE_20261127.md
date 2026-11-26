# Precursor Genome sensitivity freeze

Date frozen: 2026-11-27

Status: frozen after source admission and before any
Precursor Genome method score was calculated.

The primary analysis uses all 102 independent query reactions and all 418
cases. Three secondary analyses are fixed here to test whether a single source
property explains the primary direction:

1. **Quality 1 only.** Restrict queries to the 80 records with human quality
   score 1. Keep each selected query's closed, true-omission and
   absent-omission cases.
2. **Unreacted reactions only.** Restrict queries to the 87 reactions labelled
   `unreacted`. Keep each selected query's closed, true-omission and
   absent-omission cases.
3. **Omitted phase weight at least 5%.** Keep every closed case, every
   absent-omission control, and only true-omission cases whose omitted source
   phase has fitted weight at least `0.05`. Eight low-weight positive cases are
   excluded; no negative control is removed.

Each analysis repeats the same paired cluster bootstrap over the retained
physical reactions. Intervals are descriptive robustness checks, not new
primary endpoints. A sign change in a small subset is reported as such and is
not used to relabel the source after seeing the result.

The unreacted subset contains 87 binary reactions and therefore has no true
omission that retains two true candidates. Its retained-order endpoint is
reported as not estimable; only its unknown-evidence endpoint is interpreted.
A subset without any eligible case does not trigger replacement or scanning for
a more favourable subset.

The decision rules are:

- primary result: all 102 queries;
- sensitivity supports the primary direction if the actual-minus-complete
  missing-phase AUROC interval remains above zero for the external-model
  controls;
- sensitivity is neutral if the point estimate is positive but the interval
  crosses zero;
- sensitivity conflicts if the point estimate is negative.

CrystalShift and XDecomposer are treated as library-dependent residual
controls. Shifted Pearson profile correlation is a scoring positive control
whose candidate ranking is expected to remain fixed by construction.
