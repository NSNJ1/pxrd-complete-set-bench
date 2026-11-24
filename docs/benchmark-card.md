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

A fresh-release replay then uses DeltaXRDbench v1.1.0: 30 RRUFF-Cu and 30
opXRD-Cu mixtures, each with 20 candidates and 2-3 reference phases. The
phase-AP disadvantage of the adapted external method is consistent, while the
all-present@3 effect changes significantly by source lineage. This panel is
also retrospective and its mixtures are constructed from measured single-phase
profiles.

## External-source tests

Two fixed external-source cohorts are kept outside the seven-source core:

- opXRD EMPA: 200 measured two-phase queries, four independent COD candidates;
- RealBind mini: 104 measured single-phase queries and 104 structure candidates.
- NASA CheMin v0.2: 44 measured complete-family queries, 20 candidate families
  and 58 CC0 COD reference profiles.

Both are external retrospective tests. Their scores are not pooled with the
core benchmark. Full protocols, selected spectra, candidate provenance, result
hashes and exact reproduction checks are under `evidence/external-sources/`.
Both derive from opXRD-linked resources; they are distinct tasks and cohorts,
not independent underlying source families.

CheMin contributes a new instrument, Co K-alpha radiation and Mars mineral
assemblages. Its current profile baselines do not exceed the leakage-controlled
frequency prior on whole-set AP, so it is source-coverage and prevalence-shortcut
evidence rather than method-superiority evidence.

## Candidate-structure dependence

A separate audit covers 12 candidate collections and 1,599 unique CIFs.
Candidate libraries are not structure-disjoint:

- RealBind and opXRD reuse structures extensively;
- CheMin reference structures overlap RRUFF-derived benchmark structures;
- AriadneX candidates occur in broader structure libraries;
- anonymous prototype overlap is common but is not counted as leakage.

Consequently, the benchmark supports source-stratified query transfer. It does
not support a claim of unseen crystal-structure generalization. Full methods,
unavailable CSD/ICSD sources and aggregate results are in
`docs/structure-overlap-audit.md`.

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
Candidate structure reuse must be reported separately from query and label
leakage.
