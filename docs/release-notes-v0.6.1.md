# PXRD-CompleteSetBench v0.6.1

This release narrows the benchmark claim to complete-set review under a frozen
known candidate library and adds an endpoint-sensitivity result. The seven-
source score table is unchanged.

## New evidence

- An endpoint rank-reversal audit over the eight-method panel.
- Ten thousand query-level bootstrap repeats with rank intervals.
- Separate micro AP, macro AP, fixed all-present@k, legal tie-minimum and
  tie-maximum endpoints.
- An exact replay check for the rank-reversal result.
- A 20-query, 20-candidate RealBind stress panel with byte-identical repeated
  CrystalShift output.
- A 30-query, 20-family XCA stress panel using 31 official candidate
  structures, with byte-identical repeated output.
- Explicit wording that the two external tests share opXRD lineage and are not
  independent underlying source families.
- A model-agnostic partial-submission scorer with candidate, query and positive
  coverage. Missing candidates are never ranked and uncovered queries remain in
  the primary denominator.

## Main finding

On the controlled panel, 12% of comparable method pairs reverse order between
micro AP and fixed all-present@3. The bootstrap mean is 15.7% with a 95%
interval of 3.8%-33.3%. AP versus the legal tie maximum and tie-minimum versus
tie-maximum each reverse 38% of comparable pairs. XMatcher AutoMix changes from
rank 7 under fixed/tie-minimum all-present@3 to rank 1 under the legal tie
maximum.

The panel therefore tests interface compatibility and endpoint sensitivity. It
does not establish a stable community leaderboard.

The two 20-candidate panels sharpen the method-evidence result. CrystalShift
phase AP is 0.842 on RealBind versus 1.000 for eight-window Pearson. On XCA it
is 0.300 versus 0.633. The XCA all-present@3 values are 30% and 60%; the paired
difference has a 95% expert-label cluster-bootstrap interval of -51.9 to -4.0
percentage points. The external method therefore did not beat the simple
profile-similarity baseline in either source family.

## Reproduction

```bash
python scripts/audit_rank_reversal.py \
  --scores data/ariadnex_external_method_scores.csv \
  --registry data/external_method_registry.json \
  --out results/rank_reversal_audit.json \
  --repeats 10000 \
  --seed 20261123
```

Expected result SHA-256:

```text
6c94c76f009435ed0c991909b5774300a6a82a37d6578bcce9a0d3d57e437595
```

## Claim boundary

The endpoint audit is a retrospective, exploratory analysis on 25 queries. It is
not prospective validation and does not support a universal state-of-the-art
claim.

The stress panels are local adapted executions. RealBind is single phase. XCA is
an already consumed, textured thin-film cohort whose selected subset contains
no three-phase query. Neither panel is a fresh holdout or prospective result.
