# NASA CheMin COD external benchmark v0.2

## Scope

This external benchmark asks a method to retrieve the complete reported
mineral-family set from a measured Mars CheMin pattern under a frozen
20-family candidate library.

It is retrospective, closed-library and known-family retrieval. It is not
prospective validation, open-world phase discovery, or a measurement of
amorphous content.

## Source and redistribution boundary

- Measured patterns: NASA PDS MSL CheMin release 42.
- Candidate structures: Crystallography Open Database, CC0 1.0.
- Project-created reference profiles and derived tables: CC BY 4.0.

Version 0.1 used RRUFF-derived candidate profiles only for an internal
feasibility audit. Those profiles are not redistributed. The public benchmark
uses COD structures so the reference payload has a clear redistribution
boundary.

## Data

- 44 measured patterns;
- 20 opaque candidate families;
- 58 COD-derived reference profiles;
- 880 query-candidate truth rows;
- 41 CheMin sample groups;
- 6-10 positive families per query, mean 8.159.

The public blind archive contains raw spectra, opaque candidate IDs, numeric
reference profiles, the task manifest and checksums. It contains no truth,
source product IDs, sample names, folds, mineral-family labels or COD IDs.

The full evaluation archive contains evaluator-side truth, source metadata,
reference provenance, protocols, code, two complete runs and the public-tree
audit.

## Frozen baselines

All intervals resample whole CheMin sample groups, 10,000 repeats, seed
`20261124`.

| Method | Micro AP | Macro AP | Top-1 hit |
| --- | ---: | ---: | ---: |
| Deterministic hash random | 0.4020 | 0.4723 | 0.2955 |
| Leave-group-out frequency prior | **0.8520** | **0.8827** | 0.9773 |
| Global sqrt Pearson | 0.6408 | 0.7291 | **1.0000** |
| Eight-window sqrt Pearson | 0.6785 | 0.7085 | **1.0000** |

Window Pearson minus the leakage-controlled frequency prior:

- micro AP: `-0.1735`, 95% CI `[-0.2257, -0.1187]`;
- macro AP: `-0.1743`, 95% CI `[-0.2179, -0.1278]`;
- Top-1 hit: `+0.0227`, 95% CI `[0.0000, 0.0714]`.

The prespecified evidence gate therefore fails. Simple profile matching
recovers a top-ranked present family in every query, but the strongly
imbalanced CheMin prevalence prior dominates whole-set AP.

## Candidate identifiability

Across 190 candidate-family pairs, the largest cross-family profile Pearson is
`0.7322` for Bassanite-Anhydrite. No pair exceeds `0.98`, and there are no exact
duplicate reference profiles.

This supports candidate identifiability within the frozen library. It does not
resolve candidate-structure reuse across benchmark lineages, which is covered
separately in `docs/structure-overlap-audit.md`.

## Reproduction

Two complete evaluation runs are byte-identical:

- evaluation canonical SHA-256:
  `4d385a83009c0c1f47864910ece64b3e055453736bd4395ed6f5e89069519cc3`;
- predictions SHA-256:
  `2b9723620348a533f15217e3547a12aa4e1ce374deba835b2aa13670a1f42d5b`;
- public blind archive SHA-256:
  `2e3134fad775b8992284a7f7855b12dad2307d158c0c109087b847daee4c1231`;
- full evaluation archive SHA-256:
  `c566d4132a3964107310d11a17aa7eaf4acc611123aeb4ad453b422107d27203`.

Evidence:

- `evidence/external-sources/CHEMIN_COD_PUBLIC_V0_2_20261124.zip`;
- `evidence/external-sources/CHEMIN_COD_EVALUATION_V0_2_20261124.zip`;
- `results/chemin_cod_v0_2_summary.json`.

## Claim boundary

The benchmark adds a measured, cross-instrument, Co K-alpha source with a
traceable CC0 reference library. Its current baseline result is source coverage
and prevalence-shortcut evidence, not state-of-the-art method evidence.
