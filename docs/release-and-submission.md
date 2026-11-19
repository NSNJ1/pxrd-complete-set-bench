# Release and journal submission

## Does a public repository count as prior publication?

In normal computational-materials publishing, a code/data repository is not
treated as a journal article. Public release can support reproducibility and
priority.

However, authors must check:

- the target journal's code and data policy;
- whether review is single- or double-anonymous;
- whether the manuscript contains a patentable claim;
- the license terms of every third-party source.

For double-anonymous review, use an anonymized artifact link or keep the
repository private until review ends.

## What is public in this repository

- project-authored code and tests;
- derived score tables and aggregate results;
- source identifiers, licenses, and provenance notes;
- figures and figure source data;
- documentation and citation metadata.

## What is not public here

- raw measured spectra;
- complete third-party CIF collections;
- licensed database snapshots;
- API keys, credentials, or local configuration.

## Recommended submission artifact

Use a versioned GitHub release and archive that release to a DOI provider such
as Zenodo. Cite the exact version rather than the moving `main` branch.
