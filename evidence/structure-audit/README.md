# Candidate structure-overlap evidence

## Archive

- File: `STRUCTURE_OVERLAP_AUDIT_V1_20261124.zip`
- SHA-256:
  `889de310eb0dc44c638dfe1c8beacc50f3766d5191f6c9320929e03e877fa976`

The archive contains the frozen source specification, audit script, reports,
structure inventory, cross-source exact-duplicate table, same-composition
structure-pair table, anonymous-prototype pairs and source-version manifest.

It does not redistribute candidate CIF collections, ICSD records or CSD
records.

## Contract

- 12 candidate collections;
- 1,692 CIF occurrences;
- 1,599 unique CIF hashes;
- 1,599 parsed structures;
- one structure without symmetry determination;
- 743 same-composition structure pairs;
- 91 exact byte-identity clusters;
- 1,307 anonymous cross-lineage prototype pairs.

Two runs with the frozen source specification are byte-identical. The claim
boundary is in `docs/structure-overlap-audit.md`: candidate-library reuse is not
by itself training leakage, but it prevents an unseen-structure generalization
claim.
