# Naming evidence

Access date: 2026-11-19

Bounded OpenAlex searches were used to compare benchmark terminology in
materials science and PXRD. Raw retrieval payloads are retained in the separate
local naming-research folder and are not part of the software repository.

## Queries

- `materials science benchmark dataset machine learning`
- `powder X-ray diffraction benchmark`
- `materials benchmark property prediction`
- `MatBench materials`
- `crystal structure prediction benchmark materials`

The first page of 50 records was retained for each query. Five queries yielded
239 unique works.

## Title-term frequency

Within these bounded results:

| Term in title | Works |
| --- | ---: |
| benchmark | 40 |
| bench | 2 |
| dataset | 14 |
| evaluation | 5 |
| test set | 2 |

`Benchmark` is the common descriptive word. Established product names tend to
combine a domain acronym with `Bench`.

Examples visible in the retrieval:

- Matbench: https://doi.org/10.1038/s41524-020-00406-3
- PXRD-Bench: https://arxiv.org/abs/2610.16480
- X2SBench: https://arxiv.org/abs/2609.29751
- CSPBench: https://arxiv.org/abs/2407.00733
- PDEBench
- LLM4Mat-bench

## Decision

Repository slug:

`pxrd-complete-set-bench`

Display name:

`PXRD-CompleteSetBench`

The name is specific to the task, remains distinguishable from the existing
`PXRD-Bench`, and follows the materials-benchmark convention without using a
transient internal model name.
