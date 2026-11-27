# Release notes v0.8.0

Date: 2026-11-27

v0.8.0 adds a source-specific open-library intervention on Precursor Genome.
The question is whether complete-library evidence remains valid after a true
phase family is removed from the deployed candidate library.

## Evidence

- 102 measured A-Lab reactions;
- 20 candidate phase families;
- 418 closed, true-omission and absent-omission cases;
- CrystalShift, XDecomposer and a shifted-correlation positive control;
- 10,000-replicate paired cluster bootstrap;
- quality-1, unreacted-reaction and 5%-phase-weight sensitivities;
- repeated CrystalShift execution over all 21 libraries.

## Reuse disclosure

The project previously used 416 Precursor Genome queries in its closed-library
benchmark.

- 77/102 query IDs overlap the earlier cohort;
- 25 query IDs are new.

The panel is a new intervention on a previously consumed source. It is not a
fresh external holdout and not prospective.

## Main endpoint result

| Method | Actual reduced AUROC | Complete residual reused |
| --- | ---: | ---: |
| shifted Pearson control | 0.7082 | 0.5071 |
| CrystalShift | 0.8044 | 0.5024 |
| XDecomposer | 0.5633 | 0.5061 |

Only 30 true omissions leave at least two true candidates. The retained-true
order changes are 0/30, 4/30 and 0/30, respectively. Complete candidate-list
ordering is reported separately.

## Release checks

- 9,855 package checks pass;
- public/evaluator query metadata are separated;
- source and reference profiles are independent within the panel;
- repeat CrystalShift outputs are byte-identical;
- the independent execution prompt and expected-output hash verifier are
  included.

## Evaluator and documentation corrections

- Equal candidate scores are now ordered deterministically by ascending
  `phase_id` in both rank and screening diagnostics, so row order cannot change
  a frozen metric;
- the public documentation now reports the correct 64-character
  DeltaXRDbench v1.1.0 archive checksum;
- the checksum error in the immutable v0.6.2 and v0.7.0 tags is disclosed in
  [`ERRATA.md`](ERRATA.md), with no claim that the published tags were changed.

See
[`docs/open-library-precursor-genome-v0.8.md`](open-library-precursor-genome-v0.8.md).
