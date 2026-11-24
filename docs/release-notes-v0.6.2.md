# PXRD-CompleteSetBench v0.6.2

This release adds a fresh external-release replay and sharpens the central
benchmark claim from method complexity to evaluation non-portability.

## New evidence

- DeltaXRDbench dataset v1.1.0 was downloaded from its official GitHub release
  and verified against SHA-256
  `815cf737fe9166ec4e83e0aec91b01854ab4fc6cfeac481e83110bdf7de390b`.
- Two frozen 30-query panels were constructed: RRUFF-Cu and opXRD-Cu.
- Every query has exactly 20 structurally parseable candidates with at most 100
  atoms.
- The panels contain 16/14 two/three-phase RRUFF queries and 15/15 opXRD
  queries.
- CrystalShift predictions, set probabilities and all derived evaluations were
  reproduced byte-for-byte.
- Raw spectra, source CIFs and the upstream archive are not redistributed.

## Main finding

CrystalShift phase AP is 8.9 points below eight-window Pearson on RRUFF and 9.0
points below it on opXRD. The all-present@3 effect is not portable: -23.3 points
on RRUFF and +3.3 points on opXRD. The RRUFF-minus-opXRD interaction is -26.7
points with a 95% interval of -46.7 to -6.7.

The result supports a specific benchmark thesis: holding candidate size fixed
does not identify a stable method ordering across source lineage and endpoint.

## Reproduction

The evidence archive contains the protocol, scripts, source hashes, panel
metadata, evaluator-side targets, repeated predictions, method scores, query
metrics and exact replay status.

Expected status:

```text
deltaxrd20_exact_reproduction
```

## Claim boundary

DeltaXRDbench constructs its mixture tracks from measured single-phase source
profiles. The replay is therefore a fresh external benchmark release to this
project, not a new independent physical multiphase collection and not
prospective validation.
