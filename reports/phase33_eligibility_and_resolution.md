# Phase33 Eligibility and Adaptive Resolution

## 1. Waterfall

| step | eligibility_stage | row_count | reason | u_value_non_null_count | u_rank_non_null_count | true_zero_separated | missing_separated | suppressed_separated | common_fallback_disabled | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | theoretical_universe | 66424 | 2015 observed EMD universe × 19 KSIC sections | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 2 | source_candidate | 55438 | industry-specific census rows; absent combinations are not silently zero-filled | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 3 | observed_presence | 55438 | direct public proxy presence | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 4 | probable_presence | 1297 | Phase31 current-expansion rows; not promoted to repaired A1 | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 5 | negative_evidence | 50 | Phase31 stale-only rows excluded | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 6 | U_candidate | 10986 | missing source cells plus Phase32 negative-control candidates | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 7 | U_applied | 10986 | no value, rank, or allocation generated | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 8 | parent_fallback | 0 | common EMD fallback disabled for industry product | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 9 | Product_A1_eligible | 55438 | historical industry-specific spatial structure | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 10 | Product_A2_eligible | 12536 | sigungu middle-industry structure | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 11 | Product_C_eligible | 76266 | valid parent GVA and repaired industry-specific share | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |
| 12 | final_published_row | 144240 | retained development products | 0 | 0 | Y | Y | Y | Y | be70a84c29cccb612d8354c91eef54ef95eff9b8404020dc7cc28a8d597f0532 | 510c8c96d97b5bb0c1e409466478d006c49b0bd0 | partial_statistics_estimation_phase33_final | 2026-07-20T02:17:43+09:00 |

## 2. Policy

Missing industry evidence is unavailable, not zero. Common EMD fallback is disabled and U cells receive no value or rank.
