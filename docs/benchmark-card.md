# Benchmark card

## Task

Given a measured multiphase PXRD pattern and a frozen known-phase candidate
library, rank the candidate phases so that every labelled phase enters a fixed
review shortlist.

The benchmark is closed-candidate: each labelled phase must be present in the
source's frozen candidate library. Open-set rejection and phase quantification
are outside this task.

External or partial submissions use the schema in `docs/submission-format.md`.
Missing candidates are not ranked. Uncovered queries remain in the primary
denominator and also lower candidate, query and positive coverage.

## Primary endpoint

`all-present@k`: every labelled phase occurs anywhere among the first `k`
candidates.

The benchmark also reports:

- phase Average Precision;
- dominant-phase Top-1;
- phase recall@k;
- complete-set eligibility under a fixed shortlist;
- AP within a fixed baseline shortlist;
- exact-set-stratified and phase-cardinality-balanced values.

`all-present@k` is not exact-set accuracy and is not a calibrated probability.

## Controlled method comparison

The repository includes a separate 25-query control panel with eight methods:
random ranking, two Pearson baselines, an anchored-set ranking, CrystalShift.jl,
XRD-AutoAnalyzer, XMatcher AutoMix and XDecomposer. The fixed candidate library
contains four phases.

This panel asks whether methods from different implementation families can be
run under one candidate contract. It does not replace the seven-source
benchmark, and its source-specific scores are not pooled with other sources.
See `docs/external-method-validation.md` for execution and adaptation details.

Two additional stress panels use 20 candidate families. RealBind supplies 20
measured single-phase boundary queries. XCA Ni-Co-Al supplies 30 measured
single- or two-phase queries and 20 phase families represented by 31 official
structures. Both use locally adapted CrystalShift and are retrospective. They
test whether a more complex external implementation is automatically stronger
in the 20-candidate regime. See `docs/external-stress-tests.md`.

## External-source tests

Two fixed external-source cohorts are kept outside the seven-source core:

- opXRD EMPA: 200 measured two-phase queries, four independent COD candidates;
- RealBind mini: 104 measured single-phase queries and 104 structure candidates.

Both are external retrospective tests. Their scores are not pooled with the
core benchmark. Full protocols, selected spectra, candidate provenance, result
hashes and exact reproduction checks are under `evidence/external-sources/`.
Both derive from opXRD-linked resources; they are distinct tasks and cohorts,
not independent underlying source families.

## Strata

Results are reported by:

- source and acquisition regime;
- number of true phases;
- candidate-library size;
- exact query cluster;
- source role: development, calibration, negative transfer, saturated control,
  or project-locked test.

## Statistical protocol

- compare baseline and treatment on the same query and candidate library;
- resample the declared cluster with replacement;
- use paired query-level differences;
- report percentile 95% intervals;
- apply Holm correction within prespecified comparison families;
- report all-present tie intervals, not only the fixed tie-break value;
- retain negative and saturated results.

The final result uses 10,000 resamples and seed `20261118`.

The controlled method panel uses query-level resampling, 10,000 repeats and
seed `20261123`.

The RealBind 20-candidate panel resamples whole queries, 10,000 repeats and
seed `20261124`. The XCA 20-family panel resamples expert phase-region labels,
10,000 repeats and seed `20261124`.

The panel also has an endpoint rank-reversal audit. Reversals are reported
without selecting a preferred tie order: lower and upper legal bounds are
separate endpoints, and both are compared with AP and fixed-budget coverage.
This audit is retrospective and exploratory because the panel contains 25
queries.

## Claim boundary

This benchmark evaluates retrieval and review ordering. It does not establish
phase purity, quantitative phase fractions, open-set rejection, Rietveld
refinement quality, prospective performance, or universal state of the art.
