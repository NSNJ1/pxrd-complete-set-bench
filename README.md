# PXRD-CompleteSetBench

[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB.svg)](https://www.python.org/)
[![Code license: MIT](https://img.shields.io/badge/code-MIT-yellow.svg)](LICENSE)
[![Data license: CC BY 4.0](https://img.shields.io/badge/data-CC--BY--4.0-lightgrey.svg)](LICENSE-DATA)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24374677.svg)](https://doi.org/10.5281/zenodo.24374677)

A source-stratified benchmark for complete phase-set retrieval from measured
multiphase powder X-ray diffraction (PXRD) patterns.

Given one PXRD pattern and a fixed candidate library, the task is to place every
labelled phase inside a bounded review shortlist. The benchmark reports candidate
screening and within-shortlist ranking separately.

## What is included

- Seven measured-source cohorts from six public-data publications.
- 1,921 queries and 57,991 query-phase rows.
- Frozen candidate identities, relevance labels, primary-phase labels, source
  and acquisition clusters, and baseline/method scores.
- A six-method controlled comparison with sanitized evidence from two
  independent external executions.
- Two external controls: a saturated ternary-mixture cohort and a
  high-cardinality mineral cohort.
- An evaluator for Phase AP, dominant-phase Top-1, all-present@k,
  exact-set-stratified coverage, cardinality-balanced coverage, screening recall,
  and paired cluster-bootstrap intervals.
- Frozen 10,000-resample results and a one-command reproduction check.

Raw third-party spectra and licensed CIF collections are not redistributed.
They remain available from their original sources under their own terms.

## Quick start

Python 3.12 is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

Run a fast development evaluation:

```bash
pxrd-complete-set-bench evaluate data/query_phase_scores.csv \
  --bootstrap-repeats 200 \
  --output-json quick-evaluation.json
```

Run the full frozen reproduction:

```bash
python scripts/reproduce_core.py --output reproduction.json
```

The full command uses 10,000 cluster-bootstrap repeats and takes about 12 minutes
on the development machine. A successful run reports
`core_reproduction_exact_match`.

Reproduce the controlled six-method panel:

```bash
python scripts/reproduce_external_panel.py \
  --output external-panel-reproduction.json
```

A successful run reports
`external_panel_reproduction_exact_match`.

The panel prediction table and canonical result hashes are listed in
[docs/reproduction.md](docs/reproduction.md).

## Input format

`data/query_phase_scores.csv` is the executable benchmark input.

| Column | Meaning |
| --- | --- |
| `source` | Frozen source cohort |
| `query_id` | Query identity within a source |
| `cluster_id` | Independent resampling unit |
| `phase_id` | Candidate phase or family identity |
| `present` | Complete-set relevance label |
| `primary` | Optional dominant-phase label |
| `baseline_score` | Strong source-specific reference score |
| `method_score` | Score being evaluated |

Each source has a fixed candidate library. Scores are not pooled across sources
with different libraries.

## Metrics

| Metric | Meaning |
| --- | --- |
| Phase AP | Ranking quality over all candidate phases |
| all-present@k | Every true phase occurs somewhere in the first `k` results |
| dominant Top-1 | The labelled dominant phase is ranked first |
| Screening recall | True phases retained by a candidate shortlist |
| Fixed-shortlist AP | Ranking quality after candidate screening |

`all-present@k` is not exact-set accuracy. A list of size `k` may contain every
true phase and additional false positives.

Average precision treats equal scores as one threshold block. Candidate
ranking for `all-present@k` uses descending score and then ascending phase
identifier as the fixed tie break. The controlled panel also stores the
minimum and maximum over legal tie orders.

## Source cohorts

| Source | Queries | Role |
| --- | ---: | --- |
| AriadneX controlled | 25 | Retrospective project-locked external test |
| rare-earth MOF | 56 | Previously consumed exploratory cohort |
| Precursor Genome | 416 | Grouped cross-validation cohort |
| XCA Ni-Co-Al | 342 | Negative-transfer cohort |
| Ta-Sn-O | 964 | Saturated negative control |
| GALAXI validation | 57 | Source calibration cohort |
| GALAXI pristine | 61 | Project-locked source test |

See [docs/data-sources.md](docs/data-sources.md) for identifiers and licenses.
No cohort is described as prospective.

Independent execution and adaptation details for the controlled method panel
are in
[docs/external-method-validation.md](docs/external-method-validation.md).

## Repository layout

```text
src/pxrd_complete_set_bench/  evaluator and command-line interface
data/                       derived score table and source registry
docs/                       task definition, provenance, and reproduction guide
figures/                    publication figures and source data
results/                    frozen evaluation outputs
scripts/                    reproduction and public-tree checks
tests/                      unit and data-contract tests
```

## Reproducibility

The frozen input must have SHA-256:

```text
70a7e11872f50a9cddbe83ca84614462edebf99a1089a8b512a525a049ba2c2b
```

The canonical result payload must have SHA-256:

```text
347e626c53642bd7acca100b10936a565e251b1d28fa2ce3407a0e466cf69069
```

The comparison excludes only the input file path and retains all metrics,
clusters, labels, and bootstrap settings. See
[docs/reproduction.md](docs/reproduction.md).

## Scope and limitations

- Absolute scores depend on candidate libraries and acquisition regimes.
- The benchmark measures phase retrieval and review ordering. Open-set
  rejection, phase fractions, and Rietveld refinement quality are outside the
  task.
- Several source cohorts were used before the final evaluation protocol and are
  not fresh confirmations.
- The six-method comparison is retrospective and covers one 25-query measured
  source. It is not prospective validation and is smaller than the largest
  nearby benchmark.
- Published learned methods were not all executable under this exact contract.
  No unexecuted method is assigned a numeric result.

## Citation

Citation metadata are provided in [CITATION.cff](CITATION.cff). Update the paper
reference after the manuscript is public.

## Licenses

Project code is released under the [MIT License](LICENSE). Project-created
derived tables are released under [CC BY 4.0](LICENSE-DATA). Third-party
structures, spectra, metadata, and software retain their source-specific terms;
see [NOTICE](NOTICE).

## Design basis

The repository follows conventions used by established benchmarks such as
`lm-evaluation-harness`, `SWE-bench`, `Verifiable pXRD`, and the PXRD Candidate
List Retrieval Benchmark: a short task definition, a frozen data contract,
executable tests, explicit provenance, and a command that reproduces headline
results. See [docs/design-basis.md](docs/design-basis.md).
