# Results

- `evaluation_10000.json`: frozen seven-source evaluation with 10,000 cluster
  resamples and seed `20261118`.
- `reproduction_check.json`: successful reproduction check for the frozen core
  payload.
- `external_controls/`: aggregate results for the saturated ternary-mixture and
  high-cardinality mineral controls.
- `ariadnex_external_panel.json`: frozen eight-method evaluation on the controlled
  AriadneX cohort.
- `ariadnex_external_panel_reproduction.json`: exact-match check for that panel.
- `opxrd_empa_external_20261123.json`: 200-query measured two-phase external
  cohort, plus its scores and exact reproduction check.
- `realbind_mini_external_20261123.json`: 104-query, 104-candidate single-phase
  boundary cohort, plus query ranks and exact reproduction check.
- `source_overlap_audit.json`: phase-ID, element-set and repeated-positive-set
  audit for the seven core sources.
- `null_and_power_audit.json`: within-query label permutations, frequency-only
  controls and minimum detectable paired effects.
- `null_and_power_audit_reproduction.json`: byte-for-byte replay of that audit.
- `diagnostics_reproduction.json`: exact replay of the candidate-library,
  failure and risk-coverage diagnostics.
- `rank_reversal_audit.json`: 10,000-repeat endpoint rank-reversal and bootstrap
  rank-stability audit for the eight-method panel.
- `rank_reversal_audit_reproduction.json`: byte-for-byte replay of that audit.

These files are outputs, not independent validation. Source roles and claim
boundaries are defined in `docs/benchmark-card.md` and
`data/source_registry.json`.
