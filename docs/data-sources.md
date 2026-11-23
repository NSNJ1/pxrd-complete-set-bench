# Data sources

The public score table contains derived query identities, candidate identities,
relevance labels, primary-phase labels, clusters, and scores. Raw patterns and
complete CIF collections are not included.

| Source | Public identifier | Queries | Source role | Source-level license |
| --- | --- | ---: | --- | --- |
| AriadneX controlled | [10.26434/chemrxiv.15010300/v1](https://doi.org/10.26434/chemrxiv.15010300/v1) | 25 | Project-locked external test | MIT repository; nested PCD/ICSD terms retained |
| rare-earth MOF | [10.5281/zenodo.17902549](https://doi.org/10.5281/zenodo.17902549) | 56 | Exploratory cohort | CC BY 4.0 |
| Precursor Genome | [10.5281/zenodo.21285546](https://doi.org/10.5281/zenodo.21285546) | 416 | Grouped cross-validation | CC BY 4.0 |
| XCA Ni-Co-Al | [10.1038/s43588-021-00059-2](https://doi.org/10.1038/s43588-021-00059-2) | 342 | Negative transfer | BSD-3-Clause repository |
| Ta-Sn-O | [10.7298/kwe5-xc35](https://doi.org/10.7298/kwe5-xc35) | 964 | Saturated control | CC0 1.0 |
| GALAXI validation | [arXiv:2609.06908](https://arxiv.org/abs/2609.06908) | 57 | Source calibration | MIT repository |
| GALAXI pristine | [arXiv:2609.06908](https://arxiv.org/abs/2609.06908) | 61 | Project-locked source test | MIT repository |

## External controls

| Control | Public identifier | Queries | Role | Source-level license |
| --- | --- | ---: | --- | --- |
| Mangolini ternary mixtures | [10.17632/js2nzwf5md.5](https://doi.org/10.17632/js2nzwf5md.5) | 28 | Saturated external control, consumed | CC BY 4.0 |
| USGS Florida/Alabama XRD | [10.5066/P133DRW5](https://doi.org/10.5066/P133DRW5) | 65 | High-cardinality control, consumed | CC0 1.0 |

## Reuse boundary

- AriadneX is retrospective rather than prospective.
- The eight-method panel reuses AriadneX; adding methods does not create a new
  measured source.
- GALAXI validation and pristine are from the same publication.
- Mangolini and USGS have already been consumed and cannot become fresh
  confirmation after a method change.
- Ta-Sn-O is nearly saturated and has little discriminative power.

Source metadata are machine-readable in `data/source_registry.json`.
