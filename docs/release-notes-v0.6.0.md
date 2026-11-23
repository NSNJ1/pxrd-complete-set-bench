# PXRD-CompleteSetBench v0.6.0

This release adds mechanism diagnostics, an eight-method external-method panel,
two source-locked external cohorts and a source-overlap audit. The seven-source
core score table remains unchanged.

## New evidence

- Candidate-library scaling from 4 to full size with 20 deterministic
  distractor-sampling replicates.
- Failure taxonomy for complete-set success, boundary ties, rank `k+1` near
  misses, shallow omission and deep omission.
- Selective complete-set success and AP over 50%, 70%, 90% and 100% coverage.
- XMatcher Desktop 1.3.0 and XDecomposer 1.1.0 checkpoint adapters.
- A 200-query measured two-phase opXRD EMPA external cohort with four
  independent COD candidates.
- A 104-query, 104-candidate RealBind mini single-phase boundary cohort.
- Phase-ID, element-set and repeated-positive-set overlap audit.

The controlled method panel now has eight methods and four external
implementations. XMatcher and XDecomposer are local external adapters;
CrystalShift.jl and XRD-AutoAnalyzer were independently executed.

## Main findings

Candidate-library size changes conclusions. For GALAXI pristine, the project
method's all-present@3 falls from 66.2% at four candidates to 24.6% at full
library size. GALAXI validation falls from 80.2% to 26.3%, and rare-earth MOF
from 95.2% to 44.6%.

The eight-method panel demonstrates that newer implementations are not
automatically stronger. XDecomposer reaches AP 0.956 and all-present@3 92%, but
is not significantly different from global Pearson, window Pearson or
anchored-set strict after Holm correction. XMatcher AutoMix reaches AP 0.882
and is significantly below the simpler Pearson baselines.

The opXRD EMPA cohort contains 200 measured two-phase queries. Eight-window
Pearson reaches AP 0.744, while anchored-set strict reaches AP 0.453 and
all-present@2 12.5%. Its fixed all-present@3 value is 73.5%, but the legal tie
interval is 24.5-96.0%. The prespecified method-superiority gate fails.

The external protocol retains two disclosed limitations: a COD MAPbI3 occupancy
warning and an approximately 0.25% Cu K-alpha1/K-alpha2 scale difference. No
post-hoc correction was applied after the protocol was frozen.

RealBind mini reproduces the official global baseline exactly (R@1 78.85%,
R@10 90.38%). Eight-window Pearson gives R@1 87.50% and R@10 95.19%, but the
paired R@1 interval includes zero.

## Validation

- 29 unit and contract tests pass.
- Ruff check and format checks pass.
- The core 10,000-resample result reproduces exactly.
- The eight-method panel reproduces exactly.
- Diagnostics reproduce exactly.
- Both external-source datasets, protocols and evaluations reproduce exactly.

## Claim boundary

No universal state-of-the-art claim is made. The two external cohorts are
retrospective; the EMPA cohort is limited to one contribution and three phase
sets, and the RealBind mini cohort is single-phase.
