# Metric definitions

## Phase Average Precision

Average precision over the candidate phases of one source view.

Equal scores form one threshold block. AP therefore does not depend on an
arbitrary ordering of tied candidates.

## all-present@k

For a query with true set \(S^*\), the value is one when
\(S^* \subseteq S_{(1:k)}\), where \(S_{(1:k)}\) is the first `k` ranked
candidates. Otherwise it is zero.

This endpoint penalizes a missing true phase but does not penalize an extra false
phase. It is therefore not exact-set accuracy.

The main value uses descending score with ascending phase identifier as a fixed
tie break. The controlled method panel also reports the minimum and maximum
value over all legal orderings within equal-score blocks.

## Dominant-phase Top-1

The labelled dominant phase is ranked first. This endpoint is reported only when
the source contains dominant-phase labels.

## Recall@k

The fraction of the true phase set that appears in the first `k` candidates.

## Screening diagnostics

Screening recall reports how many true phases survive a fixed shortlist.
Fixed-shortlist AP reports ranking quality after restricting every method to the
same baseline shortlist. These values distinguish candidate omission from
within-shortlist ranking.

## Cluster-bootstrap interval

Queries are resampled by their declared acquisition or source cluster. The
reported interval is the 2.5th and 97.5th percentile of paired metric
differences over 10,000 resamples with seed `20261118`.
