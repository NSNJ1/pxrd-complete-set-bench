# External method validation

## Purpose

The seven source cohorts define the main retrieval benchmark. A smaller,
controlled experiment asks whether the same task can be executed with methods
built outside the immediate project pipeline.

This distinction matters. Source-wide gains alone cannot show whether a
benchmark is usable by other groups. A method panel is not a substitute for a
fresh measured source, and it is not prospective validation.

Six peer-reviewed benchmark papers in `npj Computational Materials` were
reviewed for comparison scope. They compared 6, 7, 8, 8, 15 and 20 model or
configuration rows, with a median of 8. None of the six stated a uniform
requirement that an external method be run by an unrelated third party. The
external execution used here is therefore stronger provenance than a
single-author-only comparison, not a journal rule.

## Panel

The panel uses the 25 measured controlled-mixture queries from the AriadneX
cohort. Each query has the same four-candidate library, A = CaCO3,
B = ZnO, C = TiO2 and D = SnO2. The true phase count is one, two or three.

The public prediction table contains 600 rows: six methods times 25 queries
times four candidates.

The six method rows are:

- deterministic random ranking;
- global sqrt-Pearson similarity;
- eight-window sqrt-Pearson similarity;
- anchored-set strict ranking;
- CrystalShift.jl;
- XRD-AutoAnalyzer.

Random, Pearson and anchored-set rows were frozen before the external results
were received.

## External executions

CrystalShift.jl was run at commit
`c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8` with Julia 1.10.13 on Windows x64.
Its native output is a distribution over phase combinations. Candidate scores
are the frozen marginal-inclusion adapter used by this benchmark.

XRD-AutoAnalyzer was run at commit
`bf32082521e45c0fcf5cf9ae9bd1321e76bf9012` with Python 3.11.9 and TensorFlow
2.21.0 on CPU. The official training script was run with a fixed 50 generated
spectra and 50 epochs, not the largest training budget available to the
original authors. BGMN 4.2.22 launched during inference.

Both executions used the same label-free handoff input. The external executor
did not receive the hidden outcome table, did not modify method parameters and
did not edit the output adapters. Sanitized return archives are included under
`evidence/external-methods/`. Minghao Li is publicly acknowledged for both
executions; his affiliation is not published.

## Metrics

Average precision treats equal scores as one threshold block. Candidate
rankings use descending score and then ascending phase identifier as the
fixed tie break. For all-present budgets, the release also reports the minimum
and maximum over every legal ordering within equal-score blocks.

The main interval procedure resamples whole queries with replacement and uses
10,000 repeats with seed `20261123`.

The metrics measure candidate screening and shortlist order. They do not show
phase purity, quantitative fractions, refinement quality or generalization to
new laboratories.

## Results

| Method | AP micro | AP macro | all@2 | all@3 | all@3 tie interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic random | 0.5454 | 0.6978 | 16% | 32% | 32%-32% |
| Global sqrt-Pearson | 0.9462 | 0.9833 | 60% | 88% | 88%-88% |
| Eight-window sqrt-Pearson | 0.9358 | 0.9867 | 60% | 92% | 92%-92% |
| Anchored-set strict | 0.9619 | 0.9733 | 60% | 92% | 84%-92% |
| CrystalShift.jl | 0.9420 | 0.9456 | 52% | 76% | 72%-80% |
| XRD-AutoAnalyzer | 0.9319 | 0.9567 | 60% | 80% | 72%-88% |

On this panel, anchored-set strict has the highest AP micro among the six rows.
Eight-window Pearson has the highest AP macro. Both reach the same fixed
all-present@3 value as anchored-set strict, while their tie intervals overlap.

Paired query bootstrap gives the anchored-set row a micro-AP advantage over
XRD-AutoAnalyzer of 0.0300, with 95% interval 0.0046 to 0.0572. The all@3
interval for the same pair is -0.04 to 0.28. The interval crossing zero means
that the 12-point difference in the fixed ranking is not stable to query
resampling.

These are source-specific comparisons. They do not support pooling these
scores with the other six source cohorts or declaring a universal winner.

## Method coverage claim

Version 0.5.0 expands the controlled panel from four to six rows. This is a
material improvement in executable method coverage, but it is still smaller
than the largest nearby benchmark reviewed. The manuscript must describe the
panel as retrospective and source-specific.
