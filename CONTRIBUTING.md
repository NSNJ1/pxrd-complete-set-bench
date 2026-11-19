# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/audit_public_tree.py
```

## Changes that require a new data version

Open a new version if any of the following changes:

- a source cohort or candidate library;
- a query, cluster, phase, relevance, or primary-phase label;
- a baseline or method score;
- a split role or claim boundary;
- a metric definition that changes reported results.

Do not overwrite a frozen release in place. Add a new version and document the
reason in `CHANGELOG.md`.

## Pull requests

Keep changes focused. Include:

- the scientific reason for the change;
- commands used for verification;
- whether the frozen input SHA-256 changes;
- the effect on existing results.

Do not include raw third-party spectra, restricted CIF collections, API keys, or
machine-specific configuration.
