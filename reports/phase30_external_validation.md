# Phase30 External Validation

## 1. Withheld Proxy

| validation_id | generation_proxy_family | withheld_proxy_family | row_count | rank_correlation | median_abs_percent_difference | validation_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| seoul_emd_2015_generation_vs_2024_business_proxy_withheld | 2015_economic_census | 2024_seoul_business_map | 428 | 0.9398200013467509 | 29.747796 | withheld_proxy_available_large_revision_risk | 1c3ac843b975f2b19f407e7856fc71fe22d49a6e39670c77a49dfbe74bcd9743 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| paid_private_sources | none | paid_card_mobile_excluded | 0 |  |  | excluded_by_scope_not_used_for_generation_or_validation | 1c3ac843b975f2b19f407e7856fc71fe22d49a6e39670c77a49dfbe74bcd9743 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |

## 2. Event Validation

| event_family | source_status | event_date_status | publication_date_status | validation_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buildinghub_permit_start_approval | pilot_available | separated | not_release_qualified | not_scored_phase30_requires_forward_event_archive | 91e8582b78945dc7b4a5b4461c82de1b3facb8d80d468211fc680fa9e53ad8a5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| factory_open_close | snapshot_available | incomplete | not_release_qualified | not_scored_historical_flow_incomplete | 91e8582b78945dc7b4a5b4461c82de1b3facb8d80d468211fc680fa9e53ad8a5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| powerplant_generation | candidate_required | missing | missing | not_scored_energy_module_pending | 91e8582b78945dc7b4a5b4461c82de1b3facb8d80d468211fc680fa9e53ad8a5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
| agriculture_weather_disaster | candidate_required | missing | missing | not_scored_agriculture_module_pending | 91e8582b78945dc7b4a5b4461c82de1b3facb8d80d468211fc680fa9e53ad8a5 | a9e63dbcf832a1ca7c41241a630a83c0bd0c9046 | partial_statistics_estimation_phase30_reci_local_fine | 2026-07-19T19:49:42+09:00 |
