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

The current target, npj Computational Materials, uses single-anonymized review.
A public repository can therefore be cited in the submitted manuscript. If the
target changes to a double-anonymous venue, create an anonymized mirror before
submission.

## What is public in this repository

- project-authored code and tests;
- derived score tables and aggregate results;
- sanitized return archives for the two externally executed methods;
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

The repository's `CITATION.cff` is sufficient for the Zenodo GitHub integration.
A separate `.zenodo.json` is not needed unless the release metadata later needs
fields that the CFF cannot express.
