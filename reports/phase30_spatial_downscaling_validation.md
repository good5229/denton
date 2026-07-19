# Phase30 Spatial Downscaling Validation

## 1. Sido-to-Sigungu Synthetic

| component_id | synthetic_task | share_mae | weighted_share_mae | claim_grade_candidate | selection_status | diagnostic | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S00_equal_sigungu_share | sido_to_sigungu_annual_share | 0.05126848383078826 | 0.03707563042060575 | D | baseline_reference |  | 9a8a6c1b14d8bb6503a33a79db9eb43dfe6c7e7501df098442bf0359cbdc37b5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| S0_previous_sigungu_share | sido_to_sigungu_annual_share | 0.0055092954295335355 | 0.002700727742667361 | B | selected_for_shadow_if_proxy_missing |  | 9a8a6c1b14d8bb6503a33a79db9eb43dfe6c7e7501df098442bf0359cbdc37b5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| S1_emd_proxy_stability_2015_vs_2024_seoul | withheld_proxy_stability |  |  | C | validation_only_proxy_disagreement_material | median_abs_difference=118626.605347 | 9a8a6c1b14d8bb6503a33a79db9eb43dfe6c7e7501df098442bf0359cbdc37b5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |

## 2. EMD Shadow Rule

S0 previous share and EMD proxy allocation may be used only as constrained allocation/activity signal; direct EMD actual is unavailable.
