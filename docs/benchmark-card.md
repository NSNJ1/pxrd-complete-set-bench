# Benchmark card

## Task

Given a measured multiphase PXRD pattern and a frozen known-phase candidate
library, rank the candidate phases so that every labelled phase enters a fixed
review shortlist.

The benchmark is closed-candidate: each labelled phase must be present in the
source's frozen candidate library. Open-set rejection and phase quantification
are outside this task.

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

The repository includes a separate 25-query control panel with six methods:
random ranking, two Pearson baselines, an anchored-set ranking, CrystalShift.jl
and XRD-AutoAnalyzer. The fixed candidate library contains four phases.

This panel asks whether methods from different implementation families can be
run under one candidate contract. It does not replace the seven-source
benchmark, and its source-specific scores are not pooled with other sources.
See `docs/external-method-validation.md` for execution and adaptation details.

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
- retain negative and saturated results.

The final result uses 10,000 resamples and seed `20261118`.

The controlled method panel uses query-level resampling, 10,000 repeats and
seed `20261123`.

## Claim boundary

This benchmark evaluates retrieval and review ordering. It does not establish
phase purity, quantitative phase fractions, open-set rejection, Rietveld
refinement quality, prospective performance, or universal state of the art.
