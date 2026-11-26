# Precursor Genome third measured-panel preregistration

Date frozen: 2026-11-27

Status: source selection frozen after inspecting the public ledger and archive
membership, and before running any phase-identification method on this source.

## Source

- title: Precursor Genome;
- Zenodo DOI: `10.5281/zenodo.21285546`;
- version: 1.0;
- publication date: 2026-07-09;
- dataset licence: CC BY 4.0;
- ledger repository:
  `https://github.com/lauren-walters/precursor-genome`;
- total reactions: 1,035;
- raw scans: 1,351;
- refinement cases: 1,950;
- instrument: A-Lab benchtop XRD with Cu K-alpha, 8-minute active scans;
- source truth: human-verified refinement cases and phase weights.

This source was already used in this project's closed-library benchmark. The
open-library panel is a new intervention on a previously consumed source, not a
fresh external holdout. Of the 102 selected query IDs, 77 overlap the earlier
416-query cohort and 25 are new. It is not a time-prospective cohort.

## Unit of analysis

One unit is one distinct A-Lab reaction. Multiple scans of one reaction remain
one cluster. Only the source's active scan is used. A reaction is eligible only
if:

- its active refinement case is accepted;
- its human quality score is 1 or 2;
- it contains two to four complete phases;
- its sample-level phase set exactly matches the active refinement set;
- the active XRDML member exists in `raw_scans.zip`;
- the active refinement pickle exists in `refinement_pkls.zip`;
- no physical-failure flag is set.

## Candidate-library rule

From all eligible reactions, rank phase families by descending number of
distinct reactions and break ties by phase identifier. Select the first 20
families. Retain every eligible reaction whose complete phase set is contained
in those 20 families.

This rule yields:

- 20 candidate phase families;
- 114 fully covered reactions before reference exclusion;
- 102 independent query reactions after excluding the 20 reactions used to
  construct reference profiles;
- 92 two-phase and 10 three-phase queries;
- 80 quality-1 and 22 quality-2 queries;
- minimum query phase weight `0.008978373343209542`.

## Candidate reference isolation

Reference profiles are derived from refinement pickles of 20 source reactions,
one unique reaction per candidate family where possible. Selection prefers:

1. unseen reference reaction;
2. non-manual refinement pickle;
3. quality score 1;
4. fewer phases;
5. larger fitted phase weight;
6. lexicographic sample ID.

Each reference profile uses only the selected phase's fitted peak positions,
integrated intensities and h/k/l labels. Every reaction used for any reference
profile is excluded from the query set. The query truth therefore does not
contain a reference reaction.

The source's fitted reference profiles are used directly. They are not described
as pure ab initio simulations, and their provenance remains visible in the
candidate manifest.

## Cases

For each of the 102 queries:

- one closed 20-candidate case;
- one `omit_present` case for each true phase;
- one deterministic `omit_absent` control selected by SHA-256 tie-breaking.

Expected minimum totals:

- 102 closed cases;
- at least 200 true-omission cases;
- 102 absent-omission cases;
- at least 404 total cases.

No truth or omitted identity is passed to a method.

## Methods

The primary methods are:

1. shifted Pearson reference-profile correlation, an independently scored
   positive control;
2. CrystalShift.jl at the previously frozen commit and parameters;
3. XDecomposer V_0.0.1 with its official checkpoint and benchmark-side
   reference-profile matching.

Methods receive one measured spectrum and the current candidate profiles. They
do not receive `role`, phase truth, omitted identity or the list of positive
families.

## Endpoints

The same two-endpoint definitions used for Algarve and Dara are applied:

1. retained-candidate order after true omission;
2. unknown evidence computed from the actual deployed library, compared with
   complete-residual reuse and the unavailable omitted-candidate percentile.

The primary uncertainty analysis is a 10,000-replicate paired bootstrap over the
102 reaction clusters. No candidate-row pooling is used.

## Stop conditions

The source fails admission if:

- fewer than 60 independent queries remain;
- any query truth lies outside the 20-candidate library;
- a reference reaction appears in the query set;
- a method needs truth to identify its candidate set;
- the active scan cannot be parsed;
- more than 10% of the selected reactions lack an accepted quality-1/2 active
  case.

The completed panel may support a transfer claim only after method execution,
case integrity checks and a repeated run.
