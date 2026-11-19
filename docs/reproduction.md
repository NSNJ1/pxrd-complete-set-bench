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
