# Design basis

The repository follows patterns used by established benchmarks:

| Benchmark | Pattern adopted here |
| --- | --- |
| lm-evaluation-harness | Short motivation, installation, one evaluation command, explicit task configuration, and reproducible outputs |
| SWE-bench | A named task, frozen datasets, a versioned evaluator, result artifacts, and citation metadata |
| Verifiable pXRD | Separate sections for benchmark inputs, scientific environment, experiments, evaluation code, results, and third-party notices |
| DeltaXRDbench | A compact task contract, model-agnostic scoring, explicit missing-output coverage and a retrospective/benchmark boundary |
| PXRD-Bench | Separate structural-recovery and property-style tasks instead of forcing every contribution into one leaderboard |
| RealBind | Candidate-library size, inference-time chemical information and leakage controls stated in the task |
| PXRD Candidate List Retrieval Benchmark | Explicit task scope, repository map, data description, citation file, and source-specific terms |

This project adopts those structural conventions without copying their prose or
code.

The repository name, `pxrd-complete-set-bench`, follows the common materials
benchmark pattern of a domain acronym, a task term, and a `Bench` suffix. It
describes the endpoint rather than a transient model name. See
[naming.md](naming.md) for the OpenAlex search evidence.
