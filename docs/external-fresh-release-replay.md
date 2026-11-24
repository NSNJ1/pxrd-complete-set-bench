# Fresh-release replay: DeltaXRDbench v1.1.0

## Purpose

The earlier 20-candidate panels were built directly from RealBind mini and the
XCA source release. This replay asks whether the same candidate-review question
behaves consistently on a newly released external benchmark that the project
had not previously consumed.

DeltaXRDbench v1.1.0 provides measured-profile RRUFF and opXRD mixture tracks,
hidden reference CIFs and explicit source provenance. Its mixtures are
constructed from measured single-phase profiles; they are not physically mixed
specimens.

The official release archive was checked against SHA-256
`815cf737fe9166ec4e83e0aec91b01854ab4fc6cfeac481e83110bdf7de390b`.
Raw spectra and CIFs are not redistributed in this repository.

## Frozen panels

For each source, 30 mixture records were selected by a pre-method hash rule:

| Source | Queries | Two-phase | Three-phase | Candidates per query |
| --- | ---: | ---: | ---: | ---: |
| RRUFF-Cu | 30 | 16 | 14 | 20 |
| opXRD-Cu | 30 | 15 | 15 | 20 |

Every released positive was retained. Negatives were hash-selected from
structures with at most 100 atoms that could be parsed and simulated by the
common pipeline. Candidate display order was independently hashed.

## Methods

The panel compares deterministic random ranking, global square-root Pearson,
eight-window square-root Pearson and locally adapted CrystalShift. Pearson
references use Cu Ka1/Ka2 and Gaussian FWHM 0.1 degrees. CrystalShift uses the
same fixed settings as the RealBind and XCA stress panels.

## Results

| Source | Method | Phase AP | all-present@3 |
| --- | --- | ---: | ---: |
| RRUFF | Global Pearson | 97.5% | 90.0% |
| RRUFF | Eight-window Pearson | 98.3% | 93.3% |
| RRUFF | CrystalShift adapted | 89.5% | 70.0% |
| opXRD | Global Pearson | 56.6% | 16.7% |
| opXRD | Eight-window Pearson | 57.8% | 13.3% |
| opXRD | CrystalShift adapted | 48.8% | 16.7% |

CrystalShift has a phase-AP disadvantage of roughly nine points in both source
lineages. The all-present@3 effect differs: -23.3 points on RRUFF and +3.3
points on opXRD. The RRUFF-minus-opXRD interaction is -26.7 points with a 95%
interval of -46.7 to -6.7.

This is stronger than a generic statement that a complex method loses. It shows
that fixed candidate size alone does not make the complete-set conclusion
portable: phase AP and a finite-budget complete-set endpoint can disagree, and
the disagreement can depend on source lineage.

## Reproduction

Each source was run twice and both formal prediction and set files are
byte-identical. The full evaluation is also byte-identical on replay.

Registration, result hashes and the evidence archive are recorded in
`data/external_fresh_release_registry.json`. The Julia `SparseArraysExt`
warning is retained in the evidence logs; every query completed and both
processes exited with code zero.

## Claim boundary

The replay does not establish that CrystalShift is generally inferior. It uses
one adapted configuration, two measured-profile lineages and synthetic mixtures.
It does not provide a physically mixed prospective cohort. Its contribution is
to show source- and endpoint-dependent non-portability under a fixed
20-candidate review budget.
