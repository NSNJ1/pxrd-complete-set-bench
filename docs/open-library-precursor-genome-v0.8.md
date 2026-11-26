# Precursor Genome open-library intervention

## Question

Does evidence from a complete candidate library remain valid when a true phase
family is unavailable to the deployed method?

The panel compares:

1. an actual run on the reduced library;
2. reuse of the complete-library output after masking the unavailable family;
3. the complete-library percentile of the removed family, which is a
   non-deployable shortcut;
4. an absent-phase omission control with the same reduced-library operation.

## Source reuse

The measured source is [Precursor Genome](
https://doi.org/10.5281/zenodo.21285546), CC BY 4.0.

This project previously used 416 Precursor Genome queries in its closed-library
benchmark. The present panel contains 102 query IDs:

- 77 overlap the previous cohort;
- 25 are new.

The panel is therefore a new open-library intervention on a previously consumed
source. It is not a fresh external holdout and not a prospective cohort.

The complete overlap record and hashes are in
`evidence/open-library-precursor-genome-v0.8/PRIOR_PROJECT_OVERLAP_20261127.json`.

## Panel

- 102 independent A-Lab reactions;
- 92 binary and 10 ternary source mixtures;
- 80 quality-1 and 22 quality-2 reactions;
- 20 candidate phase families;
- 20 reference reactions excluded from all query evaluation;
- 418 cases: 102 closed, 214 true omissions and 102 absent omissions;
- 8,044 case-phase truth rows;
- one active scan per physical reaction.

Candidate profiles come from source-fitted Rietveld refinement objects, not
ab initio pure-phase simulations.

## Methods

- CrystalShift.jl commit
  `c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`;
- XDecomposer V_0.0.1 official checkpoint;
- shifted Pearson profile correlation as a deterministic positive control.

## Results

| Method | Actual reduced AUROC | Complete residual reused | Lower-order endpoint changed |
| --- | ---: | ---: | ---: |
| shifted Pearson control | 0.7082 | 0.5071 | 0/30 |
| CrystalShift | 0.8044 | 0.5024 | 4/30 |
| XDecomposer | 0.5633 | 0.5061 | 0/30 |

Paired cluster-bootstrap intervals for actual-minus-reused AUROC are:

- profile control: `[0.1848, 0.2167]`;
- CrystalShift: `[0.2737, 0.3318]`;
- XDecomposer: `[0.0329, 0.0839]`.

The retained-order denominator contains only true omissions that leave at least
two true candidates. Complete candidate-list ordering changed much more often
for CrystalShift, but that is a different endpoint.

## Sensitivities

The following subsets were frozen before score inspection:

- 80 quality-1 queries;
- 87 unreacted reactions;
- true omissions with phase weight at least 5%.

All nine method-subset actual-minus-reused intervals exclude zero. The unreacted
subset contains only binary reactions, so its retained-order endpoint is not
estimable.

## Reproduction

The complete package is in
`evidence/open-library-precursor-genome-v0.8/`. It includes:

- public/evaluator data split;
- cases and reference-profile provenance;
- all three method outputs;
- repeated output and score checks;
- 10,000-replicate primary and sensitivity summaries;
- source-overlap audit;
- an independent Windows execution prompt and hash verifier.

The package-level release audit passes 9,855 checks.
`verify_manifest.py` checks every path, byte size and SHA-256 recorded in the
release manifest before method execution.

## Claim boundary

The panel supports source-specific endpoint separation and method dependence.
It does not support a universal method ranking, a SOTA claim, or a claim that
its 102 queries are all independent of prior project use.
