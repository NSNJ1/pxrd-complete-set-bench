# Notices and third-party material

## Precursor Genome

The measured source data are derived from the public Precursor Genome v1.0
record, Zenodo DOI `10.5281/zenodo.21285546`, published by Lauren Walters,
Matthew J. McDermott, Bernardus Rendy, Yuxing Fei and Gerbrand Ceder under
CC BY 4.0.

This package includes derived spectra, fitted reference profiles, selected
truth rows and benchmark outputs. It does not include the full raw-scan,
refinement-pickle or plotted-refinement archives. Source archive identifiers
and checksums are recorded in `dataset_v7/manifest.json`.

## CrystalShift.jl

The benchmark uses CrystalShift.jl at commit
`c4884ca1dbbd78135cd50f5e17141cdc0b6f43c8`. The package contains the benchmark
adapter and output hashes, not the upstream CrystalShift source tree.

## XDecomposer

The benchmark uses the official V_0.0.1 source and checkpoint. They are not
redistributed in this package. `run_xdecomposer_profile_panel.py` records the
expected local source and checkpoint roots, and exact revisions are recorded in
the release provenance.

## Project material

Project-created code is MIT licensed under `LICENSE`.

Project-created derived benchmark data are CC BY 4.0 under `LICENSE-DATA`.

Third-party software, source records and data remain subject to their original
licences and terms. No upstream licence is replaced by this notice.
