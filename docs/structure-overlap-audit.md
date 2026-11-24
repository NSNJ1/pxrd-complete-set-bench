# Candidate structure overlap audit

## Purpose

Source-level diversity does not guarantee candidate-structure independence.
This audit checks whether candidate CIFs used by different benchmark panels are
byte-identical, crystallographically equivalent at the same composition, or
members of a shared anonymous prototype.

## Coverage

The fixed audit covers 12 candidate collections:

- AriadneX controlled;
- XCA Ni-Co-Al;
- GALAXI validation and pristine;
- RealBind 20, paired-104 and hard-negative panels;
- DeltaXRD RRUFF and opXRD panels;
- CheMin COD;
- opXRD-EMPA;
- Ta-Sn-O.

There are 1,692 CIF occurrences and 1,599 unique CIF hashes. All 1,599
structures parse. One GALAXI structure cannot be assigned symmetry but remains
in the same-composition comparison.

Five of the seven core source records are covered. By query, this represents
1,449 of 1,921 core queries (75.4%). Rare-earth MOF and Precursor Genome remain
unavailable because their public releases contain CSD/ICSD identifiers or peak
lists but not candidate CIF payloads.

## Method

The audit uses:

- SHA-256 byte identity;
- pymatgen `StructureMatcher` with `ltol=0.2`, `stol=0.3`,
  `angle_tol=5 deg`, primitive cells and `scale=False`;
- the same comparison with `scale=True`;
- anonymous prototype matching within equal space-group number and primitive
  site count, using `ltol=0.3`, `stol=0.5` and `angle_tol=10 deg`.

Anonymous prototype overlap is reported as a diversity diagnostic, not as
leakage.

## Results

There are 91 cross-source byte-identical clusters:

- 83 are reuse between the RealBind paired-104 and hard-negative panels;
- 8 are exact CIF reuse between DeltaXRD-opXRD and RealBind20.

There are 743 unique same-composition structure pairs, 644 across lineages.
The count is dominated by 625 `As2O3` pairs from hard-negative construction.
Excluding `As2O3`, there are 118 pairs, 90 across lineages.

Unique structures with any cross-lineage same-composition match:

| Lineage | Matched / unique | Fraction |
| --- | ---: | ---: |
| AriadneX | 3 / 4 | 75.0% |
| RealBind | 53 / 124 | 42.7% |
| CheMin | 21 / 58 | 36.2% |
| opXRD | 42 / 376 | 11.2% |
| Ta-Sn-O | 1 / 15 | 6.7% |
| DeltaXRD-RRUFF | 28 / 433 | 6.5% |
| GALAXI | 16 / 566 | 2.8% |
| XCA Ni-Co-Al | 0 / 31 | 0.0% |

There are 1,307 anonymous prototype pairs across lineages. These are expected
for common structures such as rocksalt, spinel, fluorite, perovskite and
rutile and are not counted as leakage.

## Interpretation

The audit supports query-level and source-level transfer, but not an
unseen-structure generalization claim. Candidate libraries are not
structure-disjoint:

- RealBind and opXRD reuse candidate structures extensively;
- CheMin candidate structures overlap other benchmark lineages;
- AriadneX's four candidates occur in broader structure libraries.

A later model trained on any of these source libraries must declare candidate
exposure separately from query exposure. Candidate-library overlap is a
benchmark construction issue, not by itself evidence of label leakage.

## Reproducibility

The audit source specification, script, aggregate results and source-version
manifest are in
`evidence/structure-audit/STRUCTURE_OVERLAP_AUDIT_V1_20261124.zip`.

- source specification SHA-256:
  `8d3265fd948604fbab76559f1e280360c8754ba93f7d2d9ad7cc1f647d6ff4e9`;
- audit script SHA-256:
  `be22379c7953b91cb47ac90d49310c6009bb9c7b024cd0b335228a3275e7b219`;
- main result SHA-256:
  `c2fc64e787817ffe4ace7416b89f4e2cf133b6a78a06ac88e3422de5c87a1208`;
- evidence archive SHA-256:
  `889de310eb0dc44c638dfe1c8beacc50f3766d5191f6c9320929e03e877fa976`.

Two complete runs with the frozen source specification are byte-identical.
