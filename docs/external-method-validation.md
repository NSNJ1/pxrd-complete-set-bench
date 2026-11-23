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

The public prediction table contains 800 rows: eight methods times 25 queries
times four candidates.

The eight method rows are:

- deterministic random ranking;
- global sqrt-Pearson similarity;
- eight-window sqrt-Pearson similarity;
- anchored-set strict ranking;
- CrystalShift.jl;
- XRD-AutoAnalyzer.
- XMatcher AutoMix.
- XDecomposer.

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

XMatcher Desktop 1.3.0 was executed locally through its documented local API.
The official Windows distribution is archived at Figshare DOI
`10.6084/m9.figshare.32812985.v7` under CC BY 4.0. Its 102,322-entry database
was replaced only for the run by a four-entry database generated from the same
four frozen CIFs. A preflight request required `candidate_count == 4`, and the
original database was restored afterward. Mo K-alpha spectra were converted to
Cu K-alpha by Bragg-angle equivalence before inference.

The native AutoMix output is a ranked collection of phase combinations. For the
phase-ranking endpoint, a phase receives the maximum `single_phase_score` among
returned combinations that contain it; a phase absent from every returned
combination receives zero. This adapter is deterministic and label-free, but
it is not a calibrated posterior. The 25-query run was repeated and produced
the same prediction and raw-response hashes.

XDecomposer was run at commit
`3aec2505fa7de0f0f1e8b8f01f8b1f4bc8b96bf1` with the official `V_0.0.1`
checkpoint release under the MIT licence. The model natively returns four
decomposed component patterns and activity logits. Each component was compared
with four candidate references generated from the frozen CIFs using cosine and
derivative cosine, followed by the repository's top-peak penalty. A candidate's
score is its maximum activity-weighted slot score. The same 25-query run was
repeated exactly.

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
| XMatcher AutoMix | 0.8824 | 0.9300 | 52% | 72% | 64%-100% |
| XDecomposer | 0.9561 | 0.9800 | 64% | 92% | 84%-96% |

On this panel, anchored-set strict has the highest AP micro among the eight rows.
Eight-window Pearson has the highest AP macro. XDecomposer reaches the same
fixed all-present@3 value as those rows and the highest fixed all-present@2.
After paired bootstrap and Holm correction, however, XDecomposer is not
significantly different from global Pearson, window Pearson or anchored-set
strict. Its higher all@2 count is therefore a descriptive panel result, not
evidence of a universal winner.

The anchored-set row has a 0.0300 micro-AP advantage over XRD-AutoAnalyzer,
but its Holm-adjusted p-value is 0.18. The all@3 interval for the same pair is
-0.04 to 0.28. Neither result supports a stable winner after multiplicity
control.

The simpler global and eight-window Pearson rows have higher micro AP than
XMatcher AutoMix. Their paired differences are 0.0638 and 0.0534, both with
Holm-adjusted p-values below 0.01. XDecomposer is 0.0736 above XMatcher after
Holm correction. This pair of results is scientifically useful: a newer,
more elaborate decomposition or phase-combination workflow is not automatically
stronger than a simple similarity baseline on a small, fixed candidate panel.

These are source-specific comparisons. They do not support pooling these
scores with the other six source cohorts or declaring a universal winner.

## Failure and selective-risk diagnostics

The same 25-query panel was rerun through the frozen diagnostics program with
10,000 cluster-bootstrap repeats. At a review budget of three:

| Method | Complete-set success | Boundary-tie failure | Rank k+1 near miss |
| --- | ---: | ---: | ---: |
| Deterministic random | 32% | 0% | 68% |
| Global Pearson | 88% | 0% | 12% |
| Eight-window Pearson | 92% | 0% | 8% |
| Anchored-set strict | 92% | 0% | 8% |
| CrystalShift.jl | 76% | 4% | 20% |
| XRD-AutoAnalyzer | 80% | 12% | 8% |
| XMatcher AutoMix | 72% | 28% | 0% |
| XDecomposer | 92% | 4% | 4% |

The failure modes differ substantially by method. XMatcher's misses are mostly
equal-score ties caused by candidate absence from all returned AutoMix
combinations. XRD-AutoAnalyzer has a smaller tie problem and an eight-point
near-miss component. CrystalShift and XDecomposer each combine tie and
near-miss failures. A single "accuracy" number would erase these distinctions.

Boundary-margin confidence was not uniformly useful. At 50% coverage,
global and window Pearson retained 100% complete-set success, while CrystalShift
retained 61.5%, XRD-AutoAnalyzer 84.6%, XDecomposer 92.3% and XMatcher 100%.
The wide intervals and only 25 clusters mean these values are descriptive; they
are not calibrated probabilities and do not justify deployment thresholds.

## Method coverage claim

Version 0.5.0 expanded the controlled panel from four to six rows. The current
development branch adds two genuinely different open-source implementations,
bringing the panel to eight rows. This matches the median of eight rows in the
six reviewed npj Computational Materials benchmark papers, but it is still a
retrospective source-specific panel. It does not count as a new measured source.
