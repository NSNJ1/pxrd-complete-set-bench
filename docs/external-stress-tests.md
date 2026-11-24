# External-method stress tests

## Question

The controlled eight-method panel uses one 25-query source and four
candidates. Those results establish interface compatibility, not behaviour in
a larger phase library. Two additional stress panels ask whether the same
conclusion survives a 20-candidate setting in two different source families.

Both panels use CrystalShift.jl at commit
`c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`. Both are local adapted executions.
The result is retrospective and source-specific.

## RealBind boundary panel

The RealBind mini package supplies 104 measured single-phase opXRD records and
paired candidate structures. A seed fixed before method execution selected 20
queries and 20 candidate structures. Candidate display order and query display
order use independent hash rules. The public handoff contains no source UID,
target candidate or truth label.

| Method | Phase AP | Recall@1 | Recall@3 |
| --- | ---: | ---: | ---: |
| Deterministic random | 15.6% | 5.0% | 10.0% |
| Global Pearson | 90.8% | 85.0% | 100.0% |
| Eight-window Pearson | 100.0% | 100.0% | 100.0% |
| CrystalShift adapted | 84.2% | 75.0% | 90.0% |

CrystalShift minus eight-window Pearson is -0.1583 phase AP, with a 95%
cluster-bootstrap interval of -0.2875 to -0.0500. CrystalShift minus global
Pearson is not significant. The narrow reading is that the external
implementation did not outperform the simple strong baseline on this
single-phase boundary panel.

## XCA multiphase panel

The XCA Ni-Co-Al cohort supplies measured thin-film patterns, 31 official
candidate structures and 20 source-defined phase families. A label-independent
hash rule selected 30 records and a separate order produced the public query
IDs. The realized panel contains 18 single-phase and 12 two-phase queries.
Scores for structure variants are aggregated by family using the maximum.

| Method | Phase AP | Top-1 has a true phase | all-present@3 | all-present@5 |
| --- | ---: | ---: | ---: | ---: |
| Deterministic random | 16.3% | 6.7% | 0.0% | 10.0% |
| Global Pearson | 63.9% | 60.0% | 53.3% | 53.3% |
| Eight-window Pearson | 63.3% | 46.7% | 60.0% | 70.0% |
| Released XCA vector | 54.2% | 40.0% | 46.7% | 60.0% |
| CrystalShift adapted | 30.0% | 0.0% | 30.0% | 53.3% |

CrystalShift minus eight-window Pearson is -0.3330 phase AP, with a 95%
expert-label cluster-bootstrap interval of -0.4534 to -0.1769. The
all-present@3 difference is -30 percentage points, interval -51.9 to -4.0.
The same direction holds against global Pearson.

## Interpretation

Together the panels show that a more elaborate external phase-combination
implementation is not automatically stronger than profile similarity in a
20-candidate review task. This reinforces the benchmark's focus on candidate
library, endpoint and source conditions rather than a single model ranking.

The evidence does not establish:

- prospective performance;
- random-powder generalization, because the XCA patterns are textured films;
- a universal state of the art;
- three-phase performance in the selected XCA subset;
- a stable community leaderboard.

## Fresh-release replay

A later replay uses DeltaXRDbench dataset v1.1.0, a new external release to this
project. It selects 30 RRUFF-Cu and 30 opXRD-Cu mixtures under a frozen hash
rule. Every query has a 20-structure candidate library; the panels include
two- and three-phase queries. The official data archive is verified by SHA-256,
but raw spectra and CIFs are not redistributed.

CrystalShift phase AP is 8.9 points below eight-window Pearson on RRUFF and 9.0
points below it on opXRD. The all-present@3 effect is -23.3 points on RRUFF and
+3.3 points on opXRD. The source interaction is -26.7 points with a 95%
interval of -46.7 to -6.7. Thus the phase-AP disadvantage is portable across
these two lineages, but the complete-set conclusion is not.

See `docs/external-fresh-release-replay.md`.

## Reproduction

The evidence archives contain label-blind public inputs, evaluator-side truth,
the exact method outputs, environment metadata and byte-level reproduction
checks. Archive identifiers and result hashes are in
`data/external_stress_registry.json`.

Expected statuses:

```text
realbind20_exact_reproduction
xca20_exact_reproduction
```

The local Julia installation emitted a `SparseArraysExt` extension warning.
Every query still completed, all expected rows were written and the process
exit code was zero. The warning is retained in the archived stderr logs.
