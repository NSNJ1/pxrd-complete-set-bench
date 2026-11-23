# Reproduction guide

## Environment

Use Python 3.12 and install the repository:

```bash
python -m pip install -e .
```

## Fast checks

```bash
python -m unittest discover -s tests -v
python scripts/audit_public_tree.py
```

Run a development-scale bootstrap:

```bash
pxrd-complete-set-bench evaluate data/query_phase_scores.csv \
  --bootstrap-repeats 200 \
  --output-json quick-evaluation.json
```

## Frozen evaluation

```bash
pxrd-complete-set-bench evaluate data/query_phase_scores.csv \
  --baseline-column baseline_score \
  --method-column method_score \
  --budgets 1,2,3,4,5,10 \
  --bootstrap-repeats 10000 \
  --seed 20261118 \
  --output-json evaluation.json
```

The input SHA-256 must be:

```text
70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b
```

## One-command check

```bash
python scripts/reproduce_core.py --output reproduction.json
```

Expected status:

```text
core_reproduction_exact_match
```

Expected canonical payload SHA-256:

```text
347e626c53642bd7acca100b10936a565e251b1d28fa2ce3407a0e466cf69069
```

The comparison excludes only the machine-specific input path. All metrics,
source results, clusters, labels, budgets, and bootstrap settings remain in the
payload.

The full run uses 10,000 finite-sample cluster resamples and takes several
minutes.

## External method panel

```bash
python scripts/reproduce_external_panel.py \
  --output external-panel-reproduction.json
```

The prediction table SHA-256 must be:

```text
5df4475a8709fd6242a4cdbada50ec596ee35b796c323228243c957bc593e3d4
```

Expected status:

```text
external_panel_reproduction_exact_match
```

The canonical result payload SHA-256 must be:

```text
85da8424d4b69a11f6d2fa922362c84b26350180df68b522db85ec991b46eb44
```

The panel uses 10,000 query-level bootstrap repeats and seed `20261123`.
Sanitized external return archives and their hashes are listed in
`evidence/external-methods/README.md`.

## External-source cohorts

The opXRD EMPA and RealBind mini packages each include their frozen protocol,
data/source hashes, scripts, results and a reproduction status file. Check the
archive hashes against `evidence/external-sources/README.md`, then inspect the
embedded `RESULT_REPORT.md`, `results/evaluation.json` and
`results/reproduction_check.json`.

Expected statuses:

```text
opxrd_empa_reproduction_exact_match
realbind_mini_reproduction_exact_match
```

The opXRD source archive is identified by MD5
`e8e9800a8ecd2b7f01a764fdf77d5c53`. The RealBind mini source file is identified
by SHA-256
`00bd4742f0af524f9f88bcd98c16dfc59d4b77470597c296c34af4f6ad3d9678`.
