# Partial submission format

The public score table includes labels for reproduction. For a blind or
third-party evaluation, keep the truth table on the evaluator side and give a
model only the candidate identities and spectra.

## Truth table

The evaluator reads these columns:

| Column | Meaning |
| --- | --- |
| `source` | Frozen source cohort |
| `query_id` | Query identity within the source |
| `cluster_id` | Resampling unit |
| `phase_id` | Candidate identity |
| `present` | Reference-set label |

Extra score columns are ignored.

## Prediction table

The submission has one row per method, source, query and submitted candidate:

```csv
method_id,source,query_id,phase_id,score
my-method,galaxi_pristine,g0001,phase_17,0.91
```

Rules:

- identities and scores cannot be null;
- scores must be finite;
- the same method/source/query/phase row cannot appear twice;
- every submitted candidate must occur in the truth table;
- missing candidates are treated as not submitted, not as zero scores.

## Missing outputs

The primary endpoint keeps every truth query in the denominator. An uncovered
query receives zero complete-set success. It also lowers candidate, query and
positive coverage.

For diagnosis, the report includes endpoints prefixed with
`covered_query_`. These values are conditional on queries with at least one
prediction and must not be compared across submissions with different coverage.

Missing candidate scores never enter a ranking. Average precision is computed
only over submitted candidates, while recall remains relative to the complete
reference positive set. A missing positive therefore reduces recall even if all
other submitted candidates are correctly ranked.

## Commands

Python module:

```bash
python scripts/score_submission.py \
  --truth truth.csv \
  --predictions predictions.csv \
  --out submission-score.json \
  --budgets 1,2,3,4,5,10 \
  --repeats 10000
```

Installed command:

```bash
pxrd-complete-set-bench score-submission truth.csv predictions.csv \
  --budgets 1,2,3,4,5,10 \
  --bootstrap-repeats 10000 \
  --output-json submission-score.json
```

The public repository should release the candidate table and hide the `present`
column when operating a genuinely blind evaluation. The current repository
contains labels because it is also a reproducible research artifact.
