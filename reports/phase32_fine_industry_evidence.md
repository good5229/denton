# Phase32 Fine Industry Evidence

## 1. Public Sources

| source_file | source_family_id | grain | role | row_count | independence_status | fine_industry_promotion_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| business_employment_feature_table.csv | business_employment_related_family | sigungu×KSIC_middle | feature_or_validation_related | 29008 | related_not_fully_independent | not_promoted | 744e4c4bba8980cebc7ff4170f9043cfe46b302b44fbaa597c3bb5c540d5944d | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| kosis_employment_feature_table.csv | kosis_business_register_related | sido_or_region×industry | feature_candidate | 74268 | release_date_missing_development | not_promoted | 744e4c4bba8980cebc7ff4170f9043cfe46b302b44fbaa597c3bb5c540d5944d | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| kosis_business_feature_table.csv | kosis_business_register_related | sido_or_region×industry | validation_candidate | 145829 | same_underlying_family_as_employment | not_promoted | 744e4c4bba8980cebc7ff4170f9043cfe46b302b44fbaa597c3bb5c540d5944d | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| factory_feature_table.csv | factory_snapshot | sigungu×factory_stock | presence_support | 5535 | independent_presence_not_flow | not_promoted | 744e4c4bba8980cebc7ff4170f9043cfe46b302b44fbaa597c3bb5c540d5944d | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
| expanded_manufacturing_sigungu_ksic.csv | manufacturing_proxy_derived | sigungu×KSIC_detail | allocation_candidate | 92634 | same_lineage_diagnostic | not_promoted | 744e4c4bba8980cebc7ff4170f9043cfe46b302b44fbaa597c3bb5c540d5944d | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |

## 2. Multi Proxy

| policy_id | run_status | reason | source_family_1 | source_family_2 | contemporaneous_multi_proxy | promotion_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MP0_to_MP3 | not_run | same_grain_same_period_two_independent_families_missing | economic_census_2015_prior | seoul_business_map_2024_current | N | blocked | 5a36f36115023f0730252803b054e5b4bc5d8eec82803b66898a1fed563d09db | e1cc639cfcf98dbeb8a4b94bf42e77526d3d9dfa | partial_statistics_estimation_phase32_reci_component_promotion | 2026-07-19T20:48:12+09:00 |
