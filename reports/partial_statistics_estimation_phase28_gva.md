# Partial Statistics Estimation Phase 28-GVA

## 1. 실행 요약

Phase 28은 관측 Anchor와 예측·배분 행을 분리하고, NA1 completeness와 annual anchor backtest/forecast를 생성했다.

## 2. 목표·가격기준 불변 선언

real_growth_and_nominal_level_tracks_separated

## 3. Phase 27 재현

| check_id | expected | observed | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase27_status | service_full_collection_passed | service_full_collection_passed;strict_pseudo_separated;fine_grained_development_output_created;incumbents_retained | pass | 08ca60d02d94f58f89e338033a0ad2fbdf4e21684c0304e6c708b33c70b999c9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| service_regions | 17 | 17 | pass | 08ca60d02d94f58f89e338033a0ad2fbdf4e21684c0304e6c708b33c70b999c9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| fine_quarterly_rows | 46928 | 46928 | pass | 08ca60d02d94f58f89e338033a0ad2fbdf4e21684c0304e6c708b33c70b999c9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| fine_monthly_rows | 140784 | 140784 | pass | 08ca60d02d94f58f89e338033a0ad2fbdf4e21684c0304e6c708b33c70b999c9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 4. Prospective Archive 무결성

2026Q2=waiting_first_release, 2026Q3=pass_existing_archive_preserved_new_asof_only, 2026Q4=frozen_manifest_created_not_backdated

## 5. Population Identity Audit

| comparison_id | baseline_population_hash | challenger_population_hash | common_population_hash | excluded_population_hash | weight_vector_hash | metric_config_hash | identity_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase26_reported_SW0_vs_phase27_spatial_SW0 | 6e40ab306b1e2c9e0627289d5f08d689dc2c6b51af1bebc5ef7016ba12e347bc | 250dca636ebed98c730b15f8e38a2bdfe14128a6439399efb88cb36dbb294b4a | 1de122b05e8099d1e09804cbddf38d379740fa46d30072668fa129597290f713 | 44bc3f8b8fe6627769a79162c36e9e24669e5be0e13c6befc7d9e16fa7374d41 | a56ea29166f5a1f2a10513d8e3601fdb05632c03ba62672cf56a6faa043f1c92 | ab29798d7bd054aefeb2857403e451e074f64a23470c2937fed5bc2b5e55e445 | population_drift_explained_do_not_directly_compare | f32026b6ce5d500bd3b4a08edf04aa9ec6e530fd26175fefb9b69ad86fbaa2f4 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 6. SW0 Score Reconciliation

| metric | phase26_value | phase27_value | difference | explanation | explanation_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_share_mae | 0.0055185247244303555 | 0.0032263221529694533 | -0.002292202571460902 | Phase26 score covers broader 2020-2023 all-industry annual share population; Phase27 spatial score reuses Phase26 electricity diagnostic C00 manufacturing common population. | fully_explained_by_population_and_metric_scope_change | 85e7287e77d7f97d0bfe9e6b08ae219eea64d5f9c66a6dfaae485773d6d02f7e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| SW0_weighted_share_mae | 0.007167234232618469 | 0.007610836668433948 | 0.00044360243581547873 | Weight vector differs because Phase27 common population is manufacturing/electricity diagnostic rows. | fully_explained_by_population_and_metric_scope_change | 85e7287e77d7f97d0bfe9e6b08ae219eea64d5f9c66a6dfaae485773d6d02f7e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 7. Value Status Audit

| target_layer | value_status | quality_grade | actual_available | actual_used_in_generation | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NA1 | observed_official_actual | O | Y | Y | 11732 | 90a65e239f1bdc013ecf54b1bbea0f4d8fb8f1142d1c5a57a08b4cea95cda6f4 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| NM1 | experimental_allocation | E | N | N | 140784 | 90a65e239f1bdc013ecf54b1bbea0f4d8fb8f1142d1c5a57a08b4cea95cda6f4 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| NQ1 | development_allocation | D | N | N | 46928 | 90a65e239f1bdc013ecf54b1bbea0f4d8fb8f1142d1c5a57a08b4cea95cda6f4 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 8. Quality Grade 재분류

| quality_grade | value_status | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| D | development_allocation | 46928 | 2735c8bf6a724472f1bb9e781daeb0bbcea809ae41ffb744d8355ea94ea5828c | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| E | experimental_allocation | 140784 | 2735c8bf6a724472f1bb9e781daeb0bbcea809ae41ffb744d8355ea94ea5828c | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| O | observed_official_actual | 11732 | 2735c8bf6a724472f1bb9e781daeb0bbcea809ae41ffb744d8355ea94ea5828c | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| A | prospective_forecast | 2297 | 2735c8bf6a724472f1bb9e781daeb0bbcea809ae41ffb744d8355ea94ea5828c | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 9. NA1 Completeness

| theoretical_cell_count | observed_cell_count | observed_row_count | missing_cell_count | cell_coverage_rate | gva_weighted_coverage_rate | region_coverage_rate | industry_coverage_rate | year_coverage_rate | suppression_rate | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 14272 | 11579 | 11732 | 2693 | 0.8113088565022422 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 4e2b624bc9beb0fa359fc4f9ce03445f98163e7e7e0900acb10580b78699115f | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 10. 결측 Cell 분류

| cell_id | source_region | sigungu_code | sigungu_name | sector_code | sector_name | year | missing_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 서울특별시/001003/B00/2020 | 서울특별시 | 001003 | 용산구 | B00 | 광업 | 2020 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001003/B00/2021 | 서울특별시 | 001003 | 용산구 | B00 | 광업 | 2021 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001003/B00/2022 | 서울특별시 | 001003 | 용산구 | B00 | 광업 | 2022 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001003/B00/2023 | 서울특별시 | 001003 | 용산구 | B00 | 광업 | 2023 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001004/B00/2020 | 서울특별시 | 001004 | 성동구 | B00 | 광업 | 2020 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001005/B00/2020 | 서울특별시 | 001005 | 광진구 | B00 | 광업 | 2020 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001005/B00/2021 | 서울특별시 | 001005 | 광진구 | B00 | 광업 | 2021 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001005/B00/2022 | 서울특별시 | 001005 | 광진구 | B00 | 광업 | 2022 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001005/B00/2023 | 서울특별시 | 001005 | 광진구 | B00 | 광업 | 2023 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001006/B00/2020 | 서울특별시 | 001006 | 동대문구 | B00 | 광업 | 2020 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001006/B00/2021 | 서울특별시 | 001006 | 동대문구 | B00 | 광업 | 2021 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시/001006/B00/2022 | 서울특별시 | 001006 | 동대문구 | B00 | 광업 | 2022 | missing_source | c4ac8d22ede7c53109d4856b17f127239fa9cc1a0e0905dee6790f798fd0c42e | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 11. Annual Anchor Baseline

| policy_id | prediction_count | wmape | mape | median_ape | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN0_lag_level | 8167 | 0.0759787524974216 | 0.24759386560336272 | 0.06361940803476301 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| AN1_lag_growth | 8167 | 0.09670892345162936 | 0.35542264324237177 | 0.07627993970185919 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| AN2_parent_growth | 8167 | 0.07843441799824288 | 0.2614771869329675 | 0.06578551040605861 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 12. Annual Anchor Challenger

| policy_id | prediction_count | wmape | mape | median_ape | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ANR_shrunk_lag_parent_growth | 8167 | 0.08492637133938319 | 0.3039920939523322 | 0.06862287965270521 | challenger_development | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 13. Rolling-origin Annual Performance

| policy_id | prediction_count | wmape | mape | median_ape | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN0_lag_level | 8167 | 0.0759787524974216 | 0.24759386560336272 | 0.06361940803476301 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| AN1_lag_growth | 8167 | 0.09670892345162936 | 0.35542264324237177 | 0.07627993970185919 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| AN2_parent_growth | 8167 | 0.07843441799824288 | 0.2614771869329675 | 0.06578551040605861 | baseline | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| ANR_shrunk_lag_parent_growth | 8167 | 0.08492637133938319 | 0.3039920939523322 | 0.06862287965270521 | challenger_development | 7cea92ac68a510fbb4a946a7de7f77e7072a746614ad09f93fb628cc021135ec | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 14. 종사자 Feature Cube

| feature_source | row_count | year_count | region_count | industry_count | release_qualified | feature_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employee | 74268 | 6 | 3856 | 325 | N | materialized_development_only_release_date_missing | 3c69c51e2aeb421f02fc7c0ff7adfe1cc52e4f868cd523c3de76c3404f4cc1e6 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 15. 사업체 Feature Cube

| feature_source | row_count | year_count | region_count | industry_count | release_qualified | feature_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| business | 145829 | 6 | 3862 | 331 | N | materialized_development_only_release_date_missing | 3c69c51e2aeb421f02fc7c0ff7adfe1cc52e4f868cd523c3de76c3404f4cc1e6 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 16. Parent Nested CV

| candidate_id | nested_cv_status | mae_pp | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| PR2_dev_ridge_residual | blocked_pending_development_parent_target | not_scored | 9bc8f3b4c5ca5af828f40a2fbe83b41594f54e4c3f529d46aee11e31d74cec7d | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| PR3_dev_huber_residual | blocked_pending_development_parent_target | not_scored | 9bc8f3b4c5ca5af828f40a2fbe83b41594f54e4c3f529d46aee11e31d74cec7d | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 17. Locked Official Diagnostic

| diagnostic_id | use_status | retuning_allowed | mae_pp | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| locked_official_2025q1_2026q1 | one_time_diagnostic_only | N | not_scored_new_candidate_not_frozen | 675d5213b068ab23cf1803a86aef0eba95a52e3bc9a4c6bac55ea8c557041605 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 18. Spatial Share-change

| policy_id | share_mae | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| SW0 | 0.0032263221529694533 | retained | 7cd7e6a28646c0b56dd8c441f158e80ae2b63c23e237872c732299f93413ada2 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| SWD_feature_share_change | not_scored_structural_release_incomplete | blocked | 7cd7e6a28646c0b56dd8c441f158e80ae2b63c23e237872c732299f93413ada2 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 19. Industry Share-change

| policy_id | result | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- |
| IS0 | retained | ea4e4ac6cee98aa32a56813e6d8b45692e79443b7fe62f4e3f3c2aea0c7dcae8 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| IS_share_change_employee_business | blocked_release_ledger_incomplete | ea4e4ac6cee98aa32a56813e6d8b45692e79443b7fe62f4e3f3c2aea0c7dcae8 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 20. Quarterly Profile

| policy_id | result | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- |
| TQ1_TP1_project_profile | retained_grade_D | d28ad7eeb28541275e7f592672f2fe92ea734fb7866e925b321c4a5a0695e075 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| TQ3_service_profile | component_development_ready_not_promoted | d28ad7eeb28541275e7f592672f2fe92ea734fb7866e925b321c4a5a0695e075 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 21. Monthly Profile

| policy_id | native_monthly_source_coverage | result | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| TM0_equal_month | 0.0 | retained_grade_E | 6dab060d7f5a1c3662f12ad2a4d708cef8a31a84865137fcc998e4a43f968ac0 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| TM2_monthly_electricity | diagnostic_only | blocked_publication_date_unqualified | 6dab060d7f5a1c3662f12ad2a4d708cef8a31a84865137fcc998e4a43f968ac0 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 22. Hierarchical Reconciliation

proportional_reconciliation_same_price_basis

## 23. Coverage by Group

| theoretical_cell_count | observed_cell_count | observed_row_count | missing_cell_count | cell_coverage_rate | gva_weighted_coverage_rate | region_coverage_rate | industry_coverage_rate | year_coverage_rate | suppression_rate | input_hash | code_commit_hash | run_id | created_at | group_type | row_count | year_count | region_count | industry_count | feature_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 14272.0 | 11579.0 | 11732.0 | 2693.0 | 0.8113088565022422 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 3500aeddbfc38b31b38e254ec62f127bad6c55a169f59c1e266ddc4ed70c173d | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | NA1 |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  | 3500aeddbfc38b31b38e254ec62f127bad6c55a169f59c1e266ddc4ed70c173d | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | employee | 74268.0 | 6.0 | 3856.0 | 325.0 | materialized_development_only_release_date_missing |
|  |  |  |  |  |  |  |  |  |  | 3500aeddbfc38b31b38e254ec62f127bad6c55a169f59c1e266ddc4ed70c173d | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | business | 145829.0 | 6.0 | 3862.0 | 331.0 | materialized_development_only_release_date_missing |

## 24. Performance by Group

| group_id | metric_value | group_type | metric | policy_id | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 0.069378111393411 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 경기도 | 0.07192912902174947 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 경상남도 | 0.04732047035590623 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 경상북도 | 0.07411907114806707 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 광주광역시 | 0.058717238958444995 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 대구광역시 | 0.07636673722665259 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 대전광역시 | 0.06650363541987492 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 부산광역시 | 0.08602189871259537 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 서울특별시 | 0.0787184970005932 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 울산광역시 | 0.08286647165339335 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 인천광역시 | 0.10699029920209506 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 전라남도 | 0.09193373046737875 | region | wmape | AN0_lag_level | 1875b611a476e7c15c3c84fb38eb6352d9fd6aa613e4e1c17ec84c85fc5cbdd9 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 25. Worst Group

| group_id | metric_value | group_type | metric | policy_id | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F00 | 0.21422913071659347 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| B00 | 0.1994338184705348 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| D00 | 0.1769321925356033 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| H00 | 0.15096302857562294 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 인천광역시 | 0.10699029920209506 | region | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| J00 | 0.10027335503222196 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| A00 | 0.09826793685301988 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 전라남도 | 0.09193373046737875 | region | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| I00 | 0.08669016611240717 | industry | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 부산광역시 | 0.08602189871259537 | region | wmape | AN0_lag_level | bb3ad72b6af690ed3459ea29793a76d264119618572a21ebf3fc8574c6c17891 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 26. Material Degradation

| scope | material_degradation_count | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| annual_anchor | 0 | no_challenger_promoted | ea0d7f5fbf3b12557a4ed7863b3492483d08cca30af6ed262ca8102df9b3a8ba | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| spatial_share | 1 | SWD_blocked | ea0d7f5fbf3b12557a4ed7863b3492483d08cca30af6ed262ca8102df9b3a8ba | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 27. Interval Calibration

| interval | coverage | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | not_calibrated | placeholder_removed | 77ff5cc790eaa070e324f5cc7027f982a6dd7beb9a70290aa51ba237283c3910 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 80 | not_calibrated | placeholder_removed | 77ff5cc790eaa070e324f5cc7027f982a6dd7beb9a70290aa51ba237283c3910 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 95 | not_calibrated | placeholder_removed | 77ff5cc790eaa070e324f5cc7027f982a6dd7beb9a70290aa51ba237283c3910 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 28. Structural Uncertainty

| layer | interval_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- |
| annual_anchor | not_calibrated | 157ccccbb2862ad9b5d6634c9e42e26da0baaf6ab6fa2b10ed9b835d262580aa | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| quarterly | structural_uncertainty_interval_not_empirical | 157ccccbb2862ad9b5d6634c9e42e26da0baaf6ab6fa2b10ed9b835d262580aa | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| monthly | structural_uncertainty_interval_not_empirical | 157ccccbb2862ad9b5d6634c9e42e26da0baaf6ab6fa2b10ed9b835d262580aa | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 29. Fine Forecast Output

| source_region | sigungu_code | sigungu_name | sector_code | sector_name | actual_gva | target_year | policy_id | predicted_gva | value_status | actual_available | actual_used_in_generation | prediction_origin | knowledge_cutoff | input_hash | code_commit_hash | run_id | created_at | quality_grade | validation_target_type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 002 | 수원시 | A00 | 농업, 임업 및 어업 | 13214.0 | 2024 | AN0_lag_level | 13214.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | B00 | 광업 | 64.0 | 2024 | AN0_lag_level | 64.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | C00 | 제조업 | 8084369.0 | 2024 | AN0_lag_level | 8084369.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 46266.0 | 2024 | AN0_lag_level | 46266.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | ERS | 문화 및 기타서비스업 | 1334954.0 | 2024 | AN0_lag_level | 1334954.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | F00 | 건설업 | 1559587.0 | 2024 | AN0_lag_level | 1559587.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | G00 | 도매 및 소매업 | 2867673.0 | 2024 | AN0_lag_level | 2867673.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | H00 | 운수 및 창고업 | 1061513.0 | 2024 | AN0_lag_level | 1061513.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | I00 | 숙박 및 음식점업 | 1068027.0 | 2024 | AN0_lag_level | 1068027.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |
| 경기도 | 002 | 수원시 | J00 | 정보통신업 | 869535.0 | 2024 | AN0_lag_level | 869535.0 | prospective_forecast | N | N | ASOF_20260719_0933 | latest_observed_annual_year_2023 | b2f1fe4ae9c36617c3ffc21583346eb3ea2597c74dcc12e881fedd219f2fd125 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 | A | annual_anchor_backtest |

## 30. Forward Release Ledger

| checked_at | source_id | latest_reference_period | official_update_timestamp | query_payload | response_hash | page_hash | attachment_hash | changed_row_count | revision_count | origin_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-19T09:33:39+09:00 | service_production_index_full | current_local_snapshot |  | local_or_phase27_preserved | 2eb1dd74866a982de577a654cc787dbd2e4b77ff1743c2317b3af887d7354153 |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 2026-07-19T09:33:39+09:00 | mining_manufacturing_production_index | current_local_snapshot |  | local_or_phase27_preserved | d267f953c62f90a76c9bea3f9ca406cd4d160064bb23b6a61c82a7f82bb917f9 |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 2026-07-19T09:33:39+09:00 | annual_anchor_cube | current_local_snapshot |  | local_or_phase27_preserved | 90879059e3eece2bcc0574b8cadefdf43b3cc678da2b7e3a657d7da4689f0f2d |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 2026-07-19T09:33:39+09:00 | employee_feature_cube | current_local_snapshot |  | local_or_phase27_preserved | 4d18b3f0e66931e8f66e7251d0729737c9dadea23f5fbc0c377770d18f7eb075 |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 2026-07-19T09:33:39+09:00 | business_feature_cube | current_local_snapshot |  | local_or_phase27_preserved | 476efb95bdd1f44155cd3b2fa914bf3474e757ca57192507fae93533622f452b |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |
| 2026-07-19T09:33:39+09:00 | fine_forecast_output | current_local_snapshot |  | local_or_phase27_preserved | ec5508af11c4407d6f4951a0c2658552ff5e3d2aecff2d2096b3c0cf6c9578ce |  |  | not_scored_first_forward_snapshot | 0 | forward_release_ledger_active | 074eb0a318419e040d4e555f787eec5280dde69e499aa76bac84831995a8a800 | f0252709148d0be5c000c2b38538faf6931e28a2 | partial_statistics_estimation_phase28_gva | 2026-07-19T09:33:39+09:00 |

## 31. 2026Q4 Frozen Manifest

{
  "target_period": "2026Q4",
  "created_at": "2026-07-19T09:33:39+09:00",
  "annual_anchor_policy": "AN0_lag_level",
  "parent_policy": "QP1_G_national_growth_bridge",
  "spatial_policy": "SW0_last_annual_gva_share",
  "industry_policy": "IS0_previous_year_industry_share",
  "quarterly_profile_policy": "TP1_project_parent_proxy_profile",
  "monthly_profile_policy": "TM0_equal_month",
  "reconciliation_policy": "proportional_reconciliation_same_price_basis",
  "interval_policy": "not_calibrated_no_empirical_interval_claim",
  "fallback_policy": "last_observed_anchor_or_parent_fallback",
  "feature_release_rules": "strict_R1_R3_for_promotion;R4_pseudo_development_only",
  "parameter_hashes": "0fa55ac906b4cf957c0269f8ed706ef71d9fc275fc4bac5942db35b0bbe0f3d0",
  "population_hashes": "1de122b05e8099d1e09804cbddf38d379740fa46d30072668fa129597290f713",
  "official_actual_used": false,
  "archive_status": "frozen_manifest_not_backdated"
}

## 32. 선택정책

Annual=AN0_lag_level; Parent=QP1_G_national_growth_bridge; Spatial=SW0_last_annual_gva_share; Quarterly=TP1_project_parent_proxy_profile; Monthly=TM0_equal_month

## 33. 아직 주장할 수 없는 내용

official statistics equivalence, production use, calibrated interval coverage, monthly direct accuracy, quarterly direct GVA accuracy, PR1 reuse, strict origin-responsive parent challenger, structural-feature challenger promotion

## 34. 결론

NA1 과거 anchor는 Grade O로 재분류했다. 2024 annual anchor forecast는 생성했지만 strict release와 interval calibration이 부족해 production/official claim은 금지한다.
