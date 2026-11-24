# External-source validation

## Purpose

The seven core source cohorts answer whether complete-phase-set retrieval can be
measured under different laboratories, phase counts and candidate sizes. They
do not answer whether a new source, frozen after benchmark development, produces
the same conclusions. Two external retrospective tests were added for that
purpose. They are distinct cohorts, not two independent underlying source
families.

Neither cohort is prospective validation. Both source and labels are public and
were accessed after project development, so the correct label is **external
retrospective**.

## opXRD EMPA multiphase cohort

### Construction

The source is the EMPA contribution to opXRD
(`10.5281/zenodo.15298026`, CC BY 4.0). The official archive MD5 is
`e8e9800a8ecd2b7f01a764fdf77d5c53`. Before any method score was computed, the
protocol fixed:

- exactly two labelled phases per query;
- explicit formula and space-group numbers;
- a four-entry candidate library from independent COD structures;
- a maximum of 200 queries selected by SHA-256;
- global Pearson, eight-window Pearson, anchored-set strict and random
  baselines;
- 10,000 query-bootstrap repeats and fixed tie bounds.

Of 770 EMPA records, 270 met the frozen eligibility rules and 200 were selected.
The 200 queries contain three true sets: PbBr2+PbCl2 (123),
PbBr2+PbI2 (49) and MAPbI3+PbI2 (28).

Two source limitations are retained rather than repaired after scoring. The COD
MAPbI3 entry carries organic-site geometry/occupancy warnings, and EMPA records
often use a Cu K-alpha2 wavelength near 1.54439 A while the candidate reference
is simulated at 1.5405929 A. The resulting Bragg-angle scale difference is about
0.25%. A post-hoc angle correction was not applied because the protocol was
already frozen.

### Results

| Method | Phase AP | all@2 | all@3 |
| --- | ---: | ---: | ---: |
| Random | 0.520 | 17.0% | 56.5% |
| Global Pearson | 0.554 | 25.0% | 61.0% |
| Eight-window Pearson | 0.744 | 35.5% | 63.0% |
| Anchored-set strict | 0.453 | 12.5% | 73.5% |

The anchored method's tied scores give legal all@2 and all@3 intervals of
12.5-26.0% and 24.5-96.0%. The apparent 73.5% all@3 result is therefore not a
stable estimate.

Anchored-set minus global Pearson is -0.1015 phase AP, -12.5 points all@2 and
+12.5 points all@3. The all@3 interval is +2.0 to +22.5 points, but the tie
interval spans most of the possible range. The prespecified method-superiority
gate failed because all@2 fell instead of rising and phase AP also fell.

This is still a useful benchmark result. It shows that one headline all@k value
can reverse or disappear when AP, smaller review budgets and tie handling are
reported.

## RealBind mini single-phase cohort

RealBind 1.1.3 supplies a 104-query, 104-candidate opXRD subset with public
leakage-control manifests. The mini data are CC BY 4.0. The global mask-aware
sqrt-Pearson implementation reproduces RealBind's official R@1 and R@10 exactly:
78.85% and 90.38%.

The EMPA cohort also comes from opXRD. The two tests therefore cover different
tasks and source contributions, but not independent collection programmes.

An eight-window variant gives R@1 87.50%, R@10 95.19% and MRR 0.916. The paired
R@1 interval is 0.0 to +17.31 points, so the prespecified superiority gate is
not cleared even though MRR and query AP improve.

This cohort is a single-phase boundary test. It is not pooled with the
multiphase benchmark and does not replace the EMPA source.

## What the external evidence supports

The evidence supports four claims:

1. measured-source conclusions can be executed outside the original seven
   cohorts;
2. simple local similarity remains competitive at candidate-library sizes from
   four to 104;
3. complex methods can change one endpoint while worsening another, so AP,
   all-present@k, tie bounds and risk coverage must be reported together;
4. repository size and source count alone are weaker than a frozen protocol,
   independent candidate references and exact reproduction.

The evidence does not support a universal SOTA claim. The EMPA source is limited
to one contribution and three phase sets; the RealBind mini cohort is
single-phase. Both share opXRD lineage.

## Reproducibility

Both source tests reproduce byte-for-byte. The result, score and evidence hashes
are recorded in `data/external_source_registry.json`. Complete protocols,
selected spectra, candidate references, scripts and results are stored under
`evidence/external-sources/`.
