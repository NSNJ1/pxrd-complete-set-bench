# Release notes v0.7.0

This release adds a license-safe measured external source and a structural
leakage audit.

## NASA CheMin v0.2

- 44 measured Mars CheMin patterns from PDS release 42;
- 20 complete mineral-family candidates;
- 58 COD-derived reference profiles under CC0 1.0;
- 41 sample groups and 10,000 group-bootstrap repeats;
- blind public archive and separate evaluator archive;
- repeated evaluation and archive construction are byte-identical.

The frozen eight-window Pearson baseline reaches perfect top-one hit but lower
whole-set AP than the leakage-controlled frequency prior. The evidence gate is
reported as failed rather than reframed as a method win.

## Candidate structure overlap

The new audit parses 1,599 unique CIFs from 12 candidate collections and 1,692
file occurrences. It separates:

- exact file reuse;
- same-composition structure matching with and without lattice scaling;
- anonymous prototype overlap;
- unavailable CSD/ICSD candidate structures.

Fewer than the full set of core sources can be structurally audited because
rare-earth MOF and Precursor Genome do not publish candidate CIF payloads. The
release reports this gap explicitly and does not impute structures.

## Claim impact

The project continues to support source-stratified query transfer and
endpoint-dependent method ranking. It does not claim unseen-structure
generalization or fully structure-independent external sources.

## Erratum

The DeltaXRDbench v1.1.0 archive checksum inherited from v0.6.2 contained 63
characters rather than the required 64. The immutable v0.7.0 tag retains that
printing error. See [`ERRATA.md`](ERRATA.md) for the original and corrected
values. No data or result was changed.
