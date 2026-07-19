# Phase30 Industry Downscaling Validation

## 1. Industry Component Scorecard

| component_id | synthetic_task | row_count | share_mae | weighted_share_mae | claim_grade_candidate | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I1_manufacturing_lagged_proxy_share | lagged_proxy_vs_same_year_value_added_proxy | 9457 | 0.022311385351586655 |  | B | development_component_candidate | 2153f9a8e757bebf38e224f90bdcffe5a954182f3ec30b2581825c0b04e29691 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| I2_service_detail_index_share | constraint_and_proxy_component | 1632564 |  |  | D | component_available_direct_gva_unvalidated | 2153f9a8e757bebf38e224f90bdcffe5a954182f3ec30b2581825c0b04e29691 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |

## 2. Adaptive Industry Resolution

| rule_id | axis | condition | effective_level | fallback | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-IND-1 | industry | KSIC middle support and validation available | KSIC_middle | KSIC_section | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| R-IND-2 | industry | support scarce or crosswalk unstable | KSIC_section | industry_bundle | 05d318a81833df58ae7d1cb851ad5b5474598d61854f1dfdfe7973fffbb48c64 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
