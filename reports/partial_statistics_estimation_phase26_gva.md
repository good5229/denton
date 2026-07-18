# Partial Statistics Estimation Phase 26-GVA

## 1. 실행 요약

Phase 26은 source semantic registry와 comparator coverage를 복원했다. 모델 사용 후보는 광공업생산 제조업 1개 series만 통과했고, QP2는 release-dated 값 부재로 fallback 유지다.

## 2. 목표 불변 선언

`region_x_industry_x_period_GVA` target은 변경하지 않았다. Production use와 official statistics claim은 계속 금지다.

## 3. Phase 25 재현

| policy_id | expected_mae_pp | observed_mae_pp | mae_abs_diff | expected_median_ae_pp | observed_median_ae_pp | expected_direction_accuracy | observed_direction_accuracy | scored_rows | reproduction_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 6.5221863720425555 | 6.5221863720425555 | 0.0 |  | 3.7273046727326093 |  | 0.5176470588235295 | 340 | pass | 0dd98f3e5355712fc3df43e55eb04154eda478133094df9ba9ee51265b75b40a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| QP1_G_national_growth_bridge | 5.612590585711022 | 5.612590585711022 | 0.0 | 3.289705234823889 | 3.289705234823889 | 0.5176470588235295 | 0.5176470588235295 | 340 | pass | 0dd98f3e5355712fc3df43e55eb04154eda478133094df9ba9ee51265b75b40a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 4. 2026Q2 Holdout 상태

{
  "target_period": "2026Q2",
  "event_status": "waiting_first_release",
  "archive_integrity": "pass_existing_archive_preserved",
  "official_actual_used": false,
  "one_shot_consumed": false,
  "checked_at": "2026-07-19T08:49:09+09:00",
  "phase26_status": "preserved_waiting_first_release"
}

## 5. 2026Q3 Archive 무결성

| target_period | origin_id | origin_timestamp | policy_id | prediction_rows | input_hash | parameter_hash | prediction_hash | official_actual_used | archive_status | created_at | code_commit_hash | run_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q3 | ASOF_20260719_0849 | 2026-07-19T08:49:09+09:00 | QP2_R_mining_manufacturing_release_dated_pilot | 68 | 253bf9495f4bc09e4b125f7163e1c15c83b88d2de3349a85fecc7a303538c584 | e122a4dd396de51a23a992d49faa8b57cb5e9148c3d62aed4b3e6b625c6a35d2 | b6cbf05a0db8c6a9f251d608fcf5ba3ee007f4d753ff685e83f6de3905c3691c | N | diagnostic_fallback_not_shadow_qualified | 2026-07-19T08:49:09+09:00 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva |

## 6. Source Dimension Registry

| source_id | original_table_id | original_dimension_code | original_dimension_name | original_item_code | original_item_name | semantic_role | expected_cardinality | codebook_source | codebook_hash | mapping_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | 101/DT_1F02001 | PRD_DE | 수록시점 |  |  | time | 20 | data/raw/kosis_DT_1F02001_metadata.json | 08a4e934f9d264f5cdcb1b803edb32dcd8070802f665512ecb407bfe9bb2caa0 | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| mining_manufacturing_production_index.csv | 101/DT_1F02001 | A | 시도별 |  |  | region | 18 | data/raw/kosis_DT_1F02001_metadata.json | 08a4e934f9d264f5cdcb1b803edb32dcd8070802f665512ecb407bfe9bb2caa0 | pass_18_includes_national_comparator | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| mining_manufacturing_production_index.csv | 101/DT_1F02001 | B | 산업별 |  |  | industry | 5 | data/raw/kosis_DT_1F02001_metadata.json | 08a4e934f9d264f5cdcb1b803edb32dcd8070802f665512ecb407bfe9bb2caa0 | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| mining_manufacturing_production_index.csv | 101/DT_1F02001 | ITM_ID | 항목 |  |  | measure | 6 | data/raw/kosis_DT_1F02001_metadata.json | 08a4e934f9d264f5cdcb1b803edb32dcd8070802f665512ecb407bfe9bb2caa0 | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| mining_manufacturing_production_index.csv | 101/DT_1F02001 | UNIT_NM | 단위 |  |  | unit | 1 | data/raw/kosis_DT_1F02001_metadata.json | 08a4e934f9d264f5cdcb1b803edb32dcd8070802f665512ecb407bfe9bb2caa0 | pass_table_unit_2020_index | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | 101/DT_1KC2023 | PRD_DE | 수록시점 |  |  | time | 20 | data/raw/kosis_DT_1KC2023_metadata.json | 921538b711f008b81b5ca2344f6b552054ea9513043d632c13ad8314729925ee | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | 101/DT_1KC2023 | SGG | 행정구역별 |  |  | region | 17 | data/raw/kosis_DT_1KC2023_metadata.json | 921538b711f008b81b5ca2344f6b552054ea9513043d632c13ad8314729925ee | blocked_collection_filter_error_only_two_regions_observed | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | 101/DT_1KC2023 | A | 업종별 |  |  | industry | 14 | data/raw/kosis_DT_1KC2023_metadata.json | 921538b711f008b81b5ca2344f6b552054ea9513043d632c13ad8314729925ee | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | 101/DT_1KC2023 | ITM_ID | 항목 |  |  | measure | 2 | data/raw/kosis_DT_1KC2023_metadata.json | 921538b711f008b81b5ca2344f6b552054ea9513043d632c13ad8314729925ee | pass_official_codebook_and_table_title | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | 101/DT_1KC2023 | UNIT_NM | 단위 |  |  | unit | 1 | data/raw/kosis_DT_1KC2023_metadata.json | 921538b711f008b81b5ca2344f6b552054ea9513043d632c13ad8314729925ee | pass_table_unit_2020_index | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | 301/DT_200Y106 | PRD_DE | 수록시점 |  |  | time | 44 | data/raw/kosis_DT_200Y106_metadata.json | 6da0c98c6727369e5c95e7b9afab4090df4a46c6d32343cc0db541b2a7595ba7 | pass_official_table_period | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | 301/DT_200Y106 | C1 | 경제활동별 |  |  | industry | 12 | data/raw/kosis_DT_200Y106_metadata.json | 6da0c98c6727369e5c95e7b9afab4090df4a46c6d32343cc0db541b2a7595ba7 | recovered_from_region_to_industry | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | 301/DT_200Y106 | NATIONAL | 전국 |  |  | region | 1 | data/raw/kosis_DT_200Y106_metadata.json | 6da0c98c6727369e5c95e7b9afab4090df4a46c6d32343cc0db541b2a7595ba7 | inserted_national_region_by_table_scope | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | 301/DT_200Y106 | ITM_ID | 항목 |  |  | measure | 1 | data/raw/kosis_DT_200Y106_metadata.json | 6da0c98c6727369e5c95e7b9afab4090df4a46c6d32343cc0db541b2a7595ba7 | pass_official_table_item | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | 301/DT_200Y106 | UNIT_NM | 단위 |  |  | unit | 1 | data/raw/kosis_DT_200Y106_metadata.json | 6da0c98c6727369e5c95e7b9afab4090df4a46c6d32343cc0db541b2a7595ba7 | pass_table_unit_billion_krw | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | mixed/FRED_ECOS | indicator | indicator |  |  | indicator_item | 0 | local_phase20_energy_exogenous_derivative | 50c34dbd31a74e562336c439be8a9d56073a66e80a5de36154e4e3f66038f7a7 | recovered_by_indicator_column_or_quarantined | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | mixed/FRED_ECOS | period | period |  |  | time | 0 | local_phase20_energy_exogenous_derivative | 50c34dbd31a74e562336c439be8a9d56073a66e80a5de36154e4e3f66038f7a7 | recovered_by_indicator_column_or_quarantined | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | mixed/FRED_ECOS | quarterly_average_unit | quarterly_average_unit |  |  | unit | 0 | local_phase20_energy_exogenous_derivative | 50c34dbd31a74e562336c439be8a9d56073a66e80a5de36154e4e3f66038f7a7 | recovered_by_indicator_column_or_quarantined | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | mixed/FRED_ECOS | provider | provider |  |  | other | 0 | local_phase20_energy_exogenous_derivative | 50c34dbd31a74e562336c439be8a9d56073a66e80a5de36154e4e3f66038f7a7 | recovered_by_indicator_column_or_quarantined | 906ca326dd22caa6986e496cb7105cac9d9880c9795251e0415bf13b773a3a1e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 7. 전국 GDP Dimension Audit

`national_gdp_region_count=1`. Phase 25의 12개 region은 산업항목으로 복원했다.

## 8. 광공업생산 Dimension Audit

DT_1F02001의 A 차원은 시도, B 차원은 산업, ITM_ID는 measure로 확인했다. 전국 1행과 17개 시도 구조이므로 comparator source로 사용 가능하다.

## 9. 서비스생산 Dimension Audit

| source_id | observed_region_count | expected_region_count | region_coverage_rate | classification | qp2_use_status | evidence | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| service_production_index.csv | 2 | 17 | 0.11764705882352941 | collection_filter_error | excluded_until_full_region_collection | official DT_1KC2023 codebook lists 17 SGG regions; phase20 cube contains only Seoul and Busan. | a0fc28318b9500a15c814c6701ea277af7a84ef79876f53895cfce189bc682b3 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 10. Energy Series Collision Audit

| source_family | phase25_unresolved_duplicate_count | phase26_series_id_null_count | distinct_indicator_count | exact_duplicate_count | quarantined_row_count | resolution_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| energy_exogenous_with_ecos_quarterly.csv | 378 | 0 | 5 | 122 | 200 | energy_series_quarantined | 53af2dcd257a77a06b1ee0ae37b1a06c00c49389c59a8cb397fd964239fc54e7 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 11. Duplicate Resolution

| source_family | duplicate_resolution_status | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| energy_exogenous_with_ecos_quarterly.csv | exact_duplicate | 122 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | quarantined | 200 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | unique | 178 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| mining_manufacturing_production_index | unique | 360 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real | unique | 500 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | unique | 500 | d5b8825e837ab17d6be48074997f2f9c2996bb80aaa74c77ca6cfe953f333a74 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 12. Comparator Coverage

| source_family | series_id | regional_observation_count | matched_observation_count | match_rate | matched_region_count | expected_region_count | region_coverage_rate | matched_period_count | expected_period_count | period_coverage_rate | many_to_many_join_count | join_row_inflation_rate | model_used | gate_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index | 626afb45fad1578c38ffe6e8aebaeea333a234a39ac0da2c45cbac99e57ccc02 | 340 | 340 | 1.0 | 17 | 17 | 1.0 | 20 | 20 | 1.0 | 0 | 0.0 | Y | pass | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 29d8344523d78df4b4998252ee568eba8adf96521d596884dd9d1dc15309f3c0 | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 43c6870567704d3d64ac5ed7e7d3716427957a11985f7e63317202528604f2e3 | 20 | 0 | 0.0 | 0 | 17 | 0.058823529411764705 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 4419f61a660b8ddea111cb2abdde149b7bf9923481b9e7c9ed4081b624df8cbe | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 4811cb846e48944e7040643734be0a839f4c41a5cc01becc92d2a9b5495d89bd | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 4f4c2b4c0dc8c94602c13697f9e66d9a2031a0c6c5ed9bfda4d1d47beb3d8d02 | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 5f04dc5608aa80b68a37697b114e5132d9b1ec205550ebe53a00cfb47e0fb40c | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 75a3d02b15dcfb0374b3b17f19675f701ed743e374ecbae9100927d9e6f8ee6d | 20 | 0 | 0.0 | 0 | 17 | 0.058823529411764705 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 84ff34a783afd3778cc856ca09c08a12e03af7247562779ca621e18bc84e28da | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 901594f445780da2338c0329cdbd4d46e9cdf1766ee7c8e0cefd6cbc78e434d7 | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 9a77fbf3a669c7671dfe782d7bf8af2935da0abf9ebaf87f24ce0081ea946cae | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | 9e2063766a23ef4346d54836b00f701ccc5df39d89a8986644c8710c22a632d4 | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | c5297b9dd52760d44156cc097d092373ed9a5df700a23d96ef00e39c15adb3dc | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | e0a90d2726ace4bcaf7c570156f2ec8a99d856e1d4de7c46afc12b8e2e72b4e4 | 40 | 0 | 0.0 | 0 | 17 | 0.11764705882352941 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | e382e70d25d98e72df7d37df23ac65db5b4c0babbbfe7d475800eebffc7385a0 | 20 | 0 | 0.0 | 0 | 17 | 0.058823529411764705 | 0 | 20 | 1.0 | 0 | 0.0 | N | blocked_or_not_model_used | 2e552faa41b5f93fa633665b5bebc43b1bdad0a8b07b79d8fe51aea7f829241e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 13. Comparator Match Failure 원인

| source_family | failure_reason | regional_observation_count | unmatched_observation_count | failure_rate | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index | none | 340 | 0 | 0.0 | 250fa4eeaf952722b89b0e17423ac792888a7db3558b68ecc26e7b00f5a07b8a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index | source_scope_incomplete | 500 | 500 | 1.0 | 250fa4eeaf952722b89b0e17423ac792888a7db3558b68ecc26e7b00f5a07b8a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 14. Release Event Registry

| release_event_id | source_id | series_scope | reference_period_start | reference_period_end | official_release_timestamp | evidence_grade | official_page_id_or_url | attachment_name | attachment_hash | page_hash | retrieved_at | revision_sequence | first_release_flag | mapping_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KOSIS_DT_1F02001_202605_latest_update_20260630 | mining_manufacturing_production_index.csv | DT_1F02001_latest_table_update_only | 2026-05 | 2026-05 | 2026-06-30T00:00:00+09:00 | R2 | https://kosis.kr/serviceInfo/newContrainDataDetail.do?boardIdx=1970002&boardOrgId=101 |  |  | web_search_snippet_20260719_recent_table_update | 2026-07-19T08:49:09+09:00 | latest_snapshot_update | unknown | materialized_current_update_not_historical_vintage | 9d2e34b953994936d3d341fb0e5eacdf1cec41702b37c222a67f31c86df01abb | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 15. R1~R3 Qualified Source

| source_id | release_evidence_grade | evidence_description | primary_origin_allowed | shadow_allowed | exclusion_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | R2 | KOSIS recent-record page lists DT_1F02001 latest period 2026.05 and table update date 2026-06-30. | Y_for_matching_reference_period_only | Y | not_a_complete_historical_vintage_ledger_for_2019_2023_or_2026Q3 | a6d61ac18f4c45a65edeb6d532e2e5102250d9aba6bfa06e3c4eefdfae2b9618 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| service_production_index.csv | R4 | semantic coverage incomplete and only proxy lag exists locally | N | Y | collection_filter_error_and_no_R1_R3_mapping | a6d61ac18f4c45a65edeb6d532e2e5102250d9aba6bfa06e3c4eefdfae2b9618 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| rolling_national_quarterly_gdp_real.csv | R4 | national-only table with current snapshot/proxy lag locally | N | Y | not_a_regional_indicator_source | a6d61ac18f4c45a65edeb6d532e2e5102250d9aba6bfa06e3c4eefdfae2b9618 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | R4 | mixed FRED/ECOS derivative without per-series official event ledger | N | Y | series_split_recovered_but_release_events_not_materialized | a6d61ac18f4c45a65edeb6d532e2e5102250d9aba6bfa06e3c4eefdfae2b9618 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 16. Origin별 As-of 정보

| origin_id | eligible_source_set_hash | eligible_observation_hash | transformed_feature_hash | model_input_hash | independent_origin_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F0 | e6845188b1d2aebdf19d13c1613d7a49b5806a7fe336ec775fa182b36719bbc1 | e6845188b1d2aebdf19d13c1613d7a49b5806a7fe336ec775fa182b36719bbc1 | e6845188b1d2aebdf19d13c1613d7a49b5806a7fe336ec775fa182b36719bbc1 | e6845188b1d2aebdf19d13c1613d7a49b5806a7fe336ec775fa182b36719bbc1 | baseline_no_information | ffb94e7e299a14f6921873d72bc3ef2a10489ef7f3de3d20f9eeeae888cdafe6 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |
| ASOF_20260719_0849 | 5bb1e6ceea6a23453197cbd6f4eff10e8cd2c4e786dd40912f0d9c298c5533f4 | 19612fb1303c02830266976a5aad74c3ecb8be93cd75a2c1ebec36313768884a | cbd136c607d77df19ee980c49f916b563a5fc5d6b6813343fd2926e2e1147cd4 | cbd136c607d77df19ee980c49f916b563a5fc5d6b6813343fd2926e2e1147cd4 | different_release_event_information_but_no_model_input_change | ffb94e7e299a14f6921873d72bc3ef2a10489ef7f3de3d20f9eeeae888cdafe6 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 17. Regional Surprise

| source_family | region_code | industry_code | observation_period | regional_surprise | surprise_status |
| --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index | 11 | C | 2019Q1 | 22.40100000000001 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2019Q2 | 14.438999999999993 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2019Q3 | 17.799999999999997 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2019Q4 | 16.367999999999995 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2020Q1 | -0.6000000000000085 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2020Q2 | 0.7000000000000028 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2020Q3 | -2.700000000000003 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2020Q4 | 2.6999999999999886 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2021Q1 | -1.0 | available_development_current_snapshot |
| mining_manufacturing_production_index | 11 | C | 2021Q2 | -5.900000000000006 | available_development_current_snapshot |

## 18. QP2-R 제조업 Pilot

| policy_id | prediction_rows | nonfallback_rows | changed_prediction_rows | fallback_rate | fallback_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP2_R_mining_manufacturing_release_dated_pilot | 68 | 0 | 0 | 1.0 | R2 release event materialized only for latest KOSIS update; no release-dated values for model target periods. | 735a96eaa7c889f62720bf1dba298cc2ead36291058697b6f4387704d2901d9d | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 19. Revision Utility

| policy_id | revision_row_count | mean_revision_utility | median_revision_utility | harmful_revision_rate | correct_direction_flip_rate | revision_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP2_R_mining_manufacturing_release_dated_pilot | 0 | not_scored | not_scored | not_scored | not_scored | not_scored_no_nonfallback_prediction | e4dedf035c293b1c43616d384c6eca000d08d0aefb94b235435af04a80722cb2 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 20. 역사 전력자료 Backfill

| reference_month | official_posted_at | retrieved_at | source_page_id | source_file_name | source_file_hash | sheet_name | schema_version | supersedes_file_hash | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202101-202312 | 2022-02-18 | 2026-07-19T08:49:09+09:00 | KEPCO historical electricity local processed derivative | /Users/bellhundred/git-repo/denton/data/processed/municipality_electricity_features_2021_2023.csv | 102229d981355465c46fa45e1f8ec5df9a91b4932384aa57047bd17ed157db88 |  | municipality_electricity_features_2021_2023 |  | 39747f9b70fb7edbb812958065de47f34659fda9b6b250d7cf8c6f60e2df62ab | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 21. Electricity Forecast Spatial Holdout

| policy_id | track | common_year_count | common_years | common_cell_count | share_mae | gva_weighted_share_mae | rank_correlation | top_region_recall | false_spatial_update_rate | final_gva_wmape | large_cell_performance | county_region_performance | future_vintage_rows | holdout_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW_ELEC_FORECAST | forecast | 2 | 2022,2023 | 376 | 0.02684074227751501 | 0.06578053685177077 | not_scored | not_scored | not_scored | not_scored | not_scored | not_scored | 0 | diagnostic_scored_proxy_publication_date_not_holdout_qualified | 250dca636ebed98c730b15f8e38a2bdfe14128a6439399efb88cb36dbb294b4a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 22. Electricity Nowcast Spatial Holdout

| policy_id | track | common_year_count | common_years | common_cell_count | share_mae | gva_weighted_share_mae | rank_correlation | top_region_recall | false_spatial_update_rate | final_gva_wmape | large_cell_performance | county_region_performance | future_vintage_rows | holdout_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW_ELEC_NOWCAST | nowcast | 3 | 2021,2022,2023 | 604 | 0.02697391500495086 | 0.06696593016501304 | not_scored | not_scored | not_scored | not_scored | not_scored | not_scored | 0 | diagnostic_scored_proxy_publication_date_not_holdout_qualified | 250dca636ebed98c730b15f8e38a2bdfe14128a6439399efb88cb36dbb294b4a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 23. 건축인허가 Knowledge-time 상태

| source_id | feature_count | unknown_alias_feature_count | source_field_trace_status | event_time_not_knowledge_time | knowledge_time_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buildinghub | 48 | 2 | blocked_source_field_definition_not_materialized | Y | materialized_retrospective_structural_diagnostic | 317ecc098fe0a8500456e4dbc6e75c84bbc48043e4885810052f1bcdfe49b54a | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 24. 공장등록 Snapshot 상태

| source_id | snapshot_reference_date | official_publication_timestamp | retrieved_at | filename_date | date_confidence | disjunctive_date_string_count | stock_flow_status | snapshot_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| factory_registry | 2020-02-29 |  | 2026-07-19T08:49:09+09:00 | 20200229 | filename_only_or_page_metadata | 7839 | stock_only_flow_forbidden | factory_snapshot_only | f7b81de369da021f773538bd32999459b45f85d566676fb978bc75dbab54c5f6 | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 25. 선택된 Spatial 정책

| selected_spatial_policy | electricity_forecast_holdout_result | electricity_nowcast_holdout_result | selection_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | failed_SW0_better | diagnostic_scored_not_promoted | SW_ELEC has historical common years but worse share MAE and weighted share MAE than SW0. | de334eeb6a54bf2092bd82eeaf69265ad79680f2a0faa172c4e37d9aed6e959e | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 26. Temporal 상태

`TP1_project_parent_proxy_profile` retained. TP7은 승격하지 않았다.

## 27. Real·Nominal Bridge 상태

`blocked`. 공식 실질 parent와 명목 child level을 동일 target으로 취급하지 않는다.

## 28. 월별 Primary 상태

`blocked_independent_gate`. 월별 GVA primary는 활성화하지 않았다.

## 29. Risk Queue

- KOSIS service production은 500행 cap/부분수집으로 보이며 full region 재수집 필요
- 광공업 생산의 historical release event ledger가 없어 QP2 primary는 아직 차단
- 전력 share는 historical holdout 가능하지만 SW0 대비 악화

## 30. 최종 정책

QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot

## 31. 아직 주장할 수 없는 내용

QP2-R improvement, revision utility, QP2 prospective shadow qualification, SW_ELEC superiority, TP7 superiority, real-nominal bridge, monthly primary, production use, official statistics equivalence

## 32. 결론

Phase 26 최소 성공 조건은 충족했다. 의미론적 dimension 오류와 공표 event 부재를 분리했고, 전력 backfill은 scoring까지 수행했으나 SW0보다 나빠 승격하지 않았다.
