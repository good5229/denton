# Phase30 PoC Claim and Confidence

## 1. Claim Grade

| claim_grade | value_status | meaning | allowed_for_emd_fine_reci | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O | observed_official | direct official actual, not prediction | N | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| A | validated_forecast | same-grain direct actual backtest passed | N | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| B | validated_component_estimate | direct upper/synthetic component validation passed | Y | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| C | multi_proxy_activity_signal | withheld proxy or event validation passed | Y | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| D | constrained_allocation | upper aggregate reconciled but no direct lower validation | Y | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| E | experimental_fallback | weak proxy, equal split, or pseudo-only fallback | Y | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| U | unavailable | minimum support failed; do not create value | Y | e56818fe3cef0304f284426f6c683c657fe6c02b7872da1d63b41d64a8c4b7b3 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |

## 2. Adaptive Resolution

| rule_id | axis | condition | effective_level | fallback | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-SPACE-1 | region | emd proxy and code mapping available | emd | sigungu | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-SPACE-2 | region | small/suppressed/unstable emd support | sigungu | sido | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-IND-1 | industry | KSIC middle support and validation available | KSIC_middle | KSIC_section | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-IND-2 | industry | support scarce or crosswalk unstable | KSIC_section | industry_bundle | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-TIME-1 | time | native quarterly or component profile available | quarter | annual | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-TIME-2 | time | native monthly public source unavailable | quarter | equal_month_E | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |

## 3. Claim Grade Output

| claim_grade | effective_region_level | effective_industry_level | frequency | value_status | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D | emd | KSIC_section | quarter | activity_signal_and_constrained_allocation | 2816 | 5fafe598bd47aa2a51a689b5d30c7345e626d886ceab9c51f1db5f50a800d562 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
