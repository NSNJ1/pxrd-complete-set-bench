# Data

`query_phase_scores.csv` is the public evaluation table.

It contains derived query and phase identifiers, relevance labels, primary-phase
labels, acquisition clusters, and frozen scores. It does not contain raw
diffraction patterns or complete CIF collections.

The file is released under CC BY 4.0 subject to the third-party notices in the
repository root. Source identifiers and roles are recorded in
`source_registry.json`.

Aggregate results for the two additional controls are under
`results/external_controls/`.

`external_source_registry.json` records the two source-locked external tests,
their data and protocol hashes, evidence archives and exact reproduction
statuses.

`external_stress_registry.json` records the CrystalShift 20-candidate stress
panels on RealBind and XCA, including public evidence archives and exact replay
hashes.

`external_fresh_release_registry.json` records the DeltaXRDbench v1.1.0
fresh-release replay, its source hash, two panels and cross-source interaction.
