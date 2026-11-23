# Statistical and overlap audit

## Label-permutation null

For every core source, the number of true phases in each query is preserved
but phase identities are shuffled within that query. The permutation uses 2,000
draws with fixed seeds. This destroys the relationship between spectrum-derived
ordering and the nominated phases while retaining candidate cardinality.

All source-specific spectral scores reject the identity-permutation null at the
smallest attainable p-value of 1/2001 for all-present@3. This confirms that the
scores carry source-specific phase information; it does not show that one method
is better than another.

The frequency prior is a label-only baseline. It ranks candidates by their
leave-one-query-out positive frequency in the same source. It is not a
spectrum method.

## Frequency-prior controls

The frequency prior is strong in sources with repeated phase sets:

- rare-earth MOF: 53.6% all-present@3 versus 44.6% for the project method;
- XCA Ni-Co-Al: 70.8% versus 55.0%;
- AriadneX controlled: 60.0% versus 92.0%.

This is a warning against interpreting high complete-set coverage as spectral
reasoning when the candidate prevalence is highly imbalanced. Every future
method table should include a frequency-only null.

## Minimum detectable effects

The audit reports the 80%-power minimum detectable paired difference using
cluster-level paired outcomes. The values are design diagnostics for future
source expansion, not post-hoc proof.

Several close core-source comparisons have observed all-present@3 differences
smaller than their own detectable-effect estimates. They should remain
descriptive. In contrast, the AriadneX method-versus-frequency comparison is
above its detectable-effect estimate, but that source was already consumed and
cannot again serve as fresh confirmation.

## Source overlap

Phase identifiers are not shared across the core sources except one identifier
between GALAXI validation and XCA. Candidate element sets overlap extensively,
which is expected in materials science and is not by itself leakage. The audit
therefore reports exact phase-ID, element-set and repeated positive-set
overlap, but explicitly marks structure/prototype overlap as unavailable when
the distributed score table lacks structures.

GALAXI validation and pristine are from the same publication and remain separate
source/queue views rather than independent publications. Their scores are never
pooled.

## Leakage boundary

The RealBind mini cohort resolves the missing structural-control issue for its
own external test: RealBind publishes prototype-held-out splits and a
structure-matching audit. The seven-source core cannot be upgraded to a
structure-level leakage claim without recovering every candidate structure.
Missing structure identifiers are reported rather than imputed.
