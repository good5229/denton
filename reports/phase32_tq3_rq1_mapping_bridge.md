# Phase32 TQ3 RQ1 Mapping Bridge

## 1. Join Waterfall

| step | row_count | join_policy | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| raw_TQ3_service_rows | 9520 | source_rows | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| raw_RQ1_parent_rows | 340 | target_rows | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| period_normalization | 9520 | YYYYQn | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| region_code_normalization | 9520 | zero_padded_sido_code_no_fuzzy_name | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| industry_mapping | 0 | blocked_explicit_service_to_rq1_mapping_missing | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| price_basis_compatibility | 0 | blocked_index_vs_real_growth_bridge_not_declared | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| duplicate_resolution | 0 | not_reached | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| final_eligible_join | 0 | blocked | b3ab3453303ea944a1aff7b6f2678073cce18b0788f89b46fd292b1603907efd | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |

## 2. Bridge Scorecard

| bridge_id | canonical_key | raw_service_rows | raw_rq1_rows | final_join_rows | mapping_coverage | economic_mass_coverage | fuzzy_join_used | real_nominal_track_status | same_quarter_actual_leakage | bridge_status | temporal_claim_grade | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TQ3_RQ1_canonical_key_recovery | reference_year×quarter×sido_code×project_sector_code×price_basis×series_type | 9520 | 340 | 0 | 0.0 | 0.0 | N | separated_blocked | N | blocked_industry_mapping_and_price_basis | U | 14721ba9572ee42ef09bb3d3369fef73cce86f99d511979205e334e6a26d7124 | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
