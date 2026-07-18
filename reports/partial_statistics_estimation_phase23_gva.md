# Partial Statistics Estimation Phase 23-GVA

## 1. 실행 요약

| metric | value |
| --- | --- |
| status | provisional_official_growth_candidate_selected;official_prediction_alignment_completed;prospective_quarterly_holdout_frozen;real_nominal_bridge_blocked;quarterly_child_development_retained;monthly_primary_blocked |
| target | GVA |
| target_unchanged | True |
| official_source_file_count | 5 |
| official_target_rows | 1740 |
| primary_target_rows | 340 |
| deduplicated_target_rows | 1650 |
| growth_contribution_separated | True |
| period_key_error_rows_phase23 | 0 |
| inherited_period_key_error_rows | 15244 |
| official_industry_crosswalk_completion_rate | 1.0 |
| official_alignable_policy_count | 4 |
| price_basis_blocked_policy_count | 0 |
| missing_prediction_blocked_policy_count | 2 |
| qp0_g_official_mae_pp | 6.5221863720425555 |
| qp1_g_official_mae_pp | 5.612590585711022 |
| qp2_g_official_mae_pp | 5.612590585711022 |
| qp3_g_official_mae_pp | 5.612590585711022 |
| qp4_g_execution_status | blocked_not_evaluable_insufficient_independent_indicator_set |
| qp5_g_execution_status | blocked_not_evaluable_insufficient_monthly_source_history |
| official_direction_accuracy_best | 0.5176470588235295 |
| improved_official_quarter_count | 5 |
| worst_quarter | 2025Q1 |
| worst_region | 울산 |
| worst_industry | 건설업 |
| development_metric_best | QP1_national_bridge |
| official_metric_best | QP1_G_national_growth_bridge |
| gate_selected_policy | QP1_G_national_growth_bridge |
| independent_origin_count | 3 |
| responsive_origin_count | 0 |
| harmful_revision_rate | 0.0 |
| spatial_weight_source_count | 6 |
| annual_share_holdout_share_mae | 0.0055185247244303555 |
| selected_spatial_policy | SW0_last_annual_gva_share |
| indicator_profile_rate | 0.5733037845209683 |
| fallback_profile_rate | 0.4266962154790317 |
| selected_temporal_policy | TP7_when_indicator_available_else_TP1 |
| deflator_status | feasibility_only_not_merged |
| real_growth_track_status | official_aligned_growth_track_materialized |
| nominal_level_track_status | development_estimate_track_retained |
| replay_2025_rows | 1088 |
| official_2026q1_parent_reflected | True |
| current_2026q2_status | prospective_holdout |
| future_2026q3_q4_status | forecast_future_quarter |
| prospective_holdout_status | frozen_waiting_first_release |
| monthly_primary_status | blocked |
| uncertainty_status | scenario_only |
| production_use | False |
| official_statistics_claim | False |
| generated_at | 2026-07-19T01:29:26+09:00 |

## 2. 목표 불변 선언

| primary_target | official_quarterly_direct_target | production_use | official_statistics_claim |
| --- | --- | --- | --- |
| 지역×업종×기간별 GVA | 시도×공식 광역산업×분기 실질 전년동기 성장률 | False | False |

## 3. Phase 22 결과

Phase 22 materialized five official quarterly GRDP release documents and extracted an official province-by-broad-industry real year-on-year growth target cube. Phase 23 separates the official real growth track from nominal child-level development estimates.

## 4. Official Target Semantic Audit

| target_period | region_name | official_industry_group | row_role | primary_evaluation_flag |
| --- | --- | --- | --- | --- |
| 2025Q1 | 전국 | GRDP | target_growth | N |
| 2025Q1 | 전국 | 광업·제조업 | target_growth | N |
| 2025Q1 | 전국 | 건설업 | target_growth | N |
| 2025Q1 | 전국 | 서비스업 | target_growth | N |
| 2025Q1 | 서울 | GRDP | target_growth | Y |
| 2025Q1 | 서울 | 광업·제조업 | target_growth | Y |
| 2025Q1 | 서울 | 건설업 | target_growth | Y |
| 2025Q1 | 서울 | 서비스업 | target_growth | Y |
| 2025Q1 | 부산 | GRDP | target_growth | Y |
| 2025Q1 | 부산 | 광업·제조업 | target_growth | Y |
| 2025Q1 | 부산 | 건설업 | target_growth | Y |
| 2025Q1 | 부산 | 서비스업 | target_growth | Y |

## 5. Official Target Cardinality

| metric | expected_rows | actual_rows | duplicate_rows | missing_rows | unclassified_rows | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_extracted_growth_rows | 1740 | 1740 | 90 | 0 | 0 | pass_duplicate_print_separated | 175d9ef35d32da7739cbd7a77614d3748f37275638bad36fc8e7cc5e21c80940 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| primary_sido_broad_growth_rows | 340 | 340 | 0 | 0 | 0 | pass | 175d9ef35d32da7739cbd7a77614d3748f37275638bad36fc8e7cc5e21c80940 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 6. Official Target Lineage

| target_period | vintage_id | release_date | region_code | region_name | official_industry_group | source_page | source_file_hash | extraction_method | row_role | primary_evaluation_flag | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 00 | 전국 | GRDP | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | N | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 00 | 전국 | 광업·제조업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | N | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 00 | 전국 | 건설업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | N | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 00 | 전국 | 서비스업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | N | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 11 | 서울 | GRDP | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | Y | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 11 | 서울 | 광업·제조업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | Y | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 11 | 서울 | 건설업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | Y | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 2025Q1_first_release | 2025-06-26 | 11 | 서울 | 서비스업 | broad_current_quarter_table | 1313b9fc447299612095c6bc5a427ed5b9a9fb8e78536253455ebf689295af53 | pypdf_text_table_current_quarter_last_four_values | target_growth | Y | 322359c0a8cd30d79f985b4048a5e6f317ba99a1aca0479a12d76e6cd820b465 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 7. Period-key Specification

| target_period | year | quarter | period | period_key_rule | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | 2025 | 1 | 2025Q1 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q2 | 2025 | 2 | 2025Q2 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q3 | 2025 | 3 | 2025Q3 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q4 | 2025 | 4 | 2025Q4 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2026Q1 | 2026 | 1 | 2026Q1 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2026Q2 | 2026 | 2 | 2026Q2 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2026Q3 | 2026 | 3 | 2026Q3 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2026Q4 | 2026 | 4 | 2026Q4 | period=target_period=f'{year}Q{quarter}' | valid_period_identity | 32edcef11de38da707010a5101abce0aac59344d3feb5768fba84999f7d3cd7c | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 8. Period Integrity Audit

| artifact | checked_rows | period_error_rows | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase22_inherited_outputs | 30488 | 15244 | inherited_period_errors_detected | aedde523e12c7798fb85af233cc6316addaa8220c146fd5046acc9ebb8354ac2 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| phase23_current_outputs | 8 | 0 | pass | aedde523e12c7798fb85af233cc6316addaa8220c146fd5046acc9ebb8354ac2 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 9. Prediction Representation

| policy_id | prediction_measure | price_basis | frequency | region_level | industry_level | unit | growth_or_level | official_alignment_status | response_expected | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | real_yoy_growth | real_growth_track | quarterly | sido | official_broad | percent | growth | alignable_primary | false | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | real_yoy_growth | real_growth_track | quarterly | sido | official_broad | percent | growth | alignable_primary | false | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | real_yoy_growth | real_growth_track | quarterly | sido | official_broad | percent | growth | alignable_primary | false | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | real_yoy_growth | real_growth_track | quarterly | sido | official_broad | percent | growth | alignable_primary | false | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP4_G_factor_growth | not_materialized | not_materialized | quarterly | sido | official_broad | percent | growth | blocked_not_evaluable_insufficient_independent_indicator_set | true | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP5_G_midas_growth | not_materialized | not_materialized | quarterly | sido | official_broad | percent | growth | blocked_not_evaluable_insufficient_monthly_source_history | true | db2834321819d2cd1f8aa69f990038c67b6aafb1f4576f5c0d211590bc10bc95 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 10. Official Industry Crosswalk

| official_industry_group | project_industry_code | mapping_status | official_mapping_status | crosswalk_scope | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GRDP | TOTAL | all_industries | pass | primary_sido_broad_growth | 45ef1167c8dc7d11ff94ec294cb87f684fa648d28b1900f0e684c652bd7efbad | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 광업·제조업 | B00;C00 | official_broad | pass | primary_sido_broad_growth | 45ef1167c8dc7d11ff94ec294cb87f684fa648d28b1900f0e684c652bd7efbad | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 건설업 | F00 | official_broad | pass | primary_sido_broad_growth | 45ef1167c8dc7d11ff94ec294cb87f684fa648d28b1900f0e684c652bd7efbad | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 서비스업 | G00~S00 | official_broad | pass | primary_sido_broad_growth | 45ef1167c8dc7d11ff94ec294cb87f684fa648d28b1900f0e684c652bd7efbad | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 11. Official Prediction Alignment

| target_period | region_name | official_industry_group | policy_id | official_actual_growth_pct | predicted_growth_pct | alignment_status |
| --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | 서울 | GRDP | QP0_G_seasonal_growth | 1.0 | 3.5621833404847703 | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP1_G_national_growth_bridge | 1.0 | 3.5621833404847703 | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP2_G_indicator_growth_bridge | 1.0 | 3.5621833404847703 | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP3_G_pooled_robust_growth | 1.0 | 3.5621833404847703 | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP0_G_seasonal_growth | -4.3 | -2.813064732968873 | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP1_G_national_growth_bridge | -4.3 | 0.9945371904547806 | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP2_G_indicator_growth_bridge | -4.3 | 0.9945371904547806 | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP3_G_pooled_robust_growth | -4.3 | 0.9945371904547806 | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP0_G_seasonal_growth | -7.7 | 4.242995573262975 | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP1_G_national_growth_bridge | -7.7 | 4.242995573262975 | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP2_G_indicator_growth_bridge | -7.7 | 4.242995573262975 | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP3_G_pooled_robust_growth | -7.7 | 4.242995573262975 | aligned_primary |

## 12. QP0-G Seasonal Growth

| policy_id | scored_rows | official_mae_pp | official_median_ae_pp | official_p90_ae_pp | mean_error_pp | direction_accuracy | annual_weighted_growth_mae_pp | improved_quarter_count_vs_qp0 | evaluation_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 340 | 6.5221863720425555 | 3.7273046727326093 | 17.15005056716819 | 3.6950187925774522 | 0.5176470588235295 | 6.5221863720425555 | 0 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 13. QP1-G National Growth Bridge

| policy_id | scored_rows | official_mae_pp | official_median_ae_pp | official_p90_ae_pp | mean_error_pp | direction_accuracy | annual_weighted_growth_mae_pp | improved_quarter_count_vs_qp0 | evaluation_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_G_national_growth_bridge | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 14. QP2-G Indicator Growth Bridge

| policy_id | scored_rows | official_mae_pp | official_median_ae_pp | official_p90_ae_pp | mean_error_pp | direction_accuracy | annual_weighted_growth_mae_pp | improved_quarter_count_vs_qp0 | evaluation_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP2_G_indicator_growth_bridge | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 15. QP3-G Pooled Robust Growth

| policy_id | scored_rows | official_mae_pp | official_median_ae_pp | official_p90_ae_pp | mean_error_pp | direction_accuracy | annual_weighted_growth_mae_pp | improved_quarter_count_vs_qp0 | evaluation_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP3_G_pooled_robust_growth | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 16. QP4-G Factor Growth

blocked_not_evaluable_insufficient_independent_indicator_set

## 17. QP5-G MIDAS Growth

blocked_not_evaluable_insufficient_monthly_source_history

## 18. Official First-release Accuracy

| policy_id | scored_rows | official_mae_pp | official_median_ae_pp | official_p90_ae_pp | mean_error_pp | direction_accuracy | annual_weighted_growth_mae_pp | improved_quarter_count_vs_qp0 | evaluation_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_G_national_growth_bridge | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 340 | 5.612590585711022 | 3.289705234823889 | 13.944300974159692 | 3.6592446404128127 | 0.5176470588235295 | 5.612590585711022 | 5 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 340 | 6.5221863720425555 | 3.7273046727326093 | 17.15005056716819 | 3.6950187925774522 | 0.5176470588235295 | 6.5221863720425555 | 0 | retrospective_external_evaluation | d7bde52bab24835c427a3dc40f9b7c01b02dedd0f110ec72b859ec3a2b96f4bc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 19. Official Direction Accuracy

| policy_id | direction_accuracy | near_zero_direction_accuracy | scored_rows | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 0.5176470588235295 | 0.5176470588235295 | 340 | cfe593b39bfdc5cd9bee5bda5ead723d3cba2ebd42dd15ffa972f615f69a2631 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 0.5176470588235295 | 0.5176470588235295 | 340 | cfe593b39bfdc5cd9bee5bda5ead723d3cba2ebd42dd15ffa972f615f69a2631 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 0.5176470588235295 | 0.5176470588235295 | 340 | cfe593b39bfdc5cd9bee5bda5ead723d3cba2ebd42dd15ffa972f615f69a2631 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 0.5176470588235295 | 0.5176470588235295 | 340 | cfe593b39bfdc5cd9bee5bda5ead723d3cba2ebd42dd15ffa972f615f69a2631 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 20. Quarter별 비교

| policy_id | target_period | official_mae_pp | median_ae_pp | direction_accuracy | scored_rows | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 2025Q1 | 8.152018698099834 | 4.894070867111188 | 0.4264705882352941 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q2 | 6.949027458647618 | 4.630816139135532 | 0.4264705882352941 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q3 | 6.196318558654144 | 3.1185686689210117 | 0.5294117647058824 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q4 | 5.177459433035576 | 2.913269594166862 | 0.5735294117647058 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2026Q1 | 6.1361077117756055 | 3.007989642798835 | 0.6323529411764706 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q1 | 7.688504213777702 | 4.419109970597145 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q2 | 6.4714002402089985 | 4.458692187415718 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q3 | 5.08853744904713 | 2.9511480445583267 | 0.5588235294117647 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q4 | 3.781781012951428 | 2.640805524240651 | 0.6176470588235294 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2026Q1 | 5.032730012569852 | 2.657120963131931 | 0.6470588235294118 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q1 | 7.688504213777702 | 4.419109970597145 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q2 | 6.4714002402089985 | 4.458692187415718 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q3 | 5.08853744904713 | 2.9511480445583267 | 0.5588235294117647 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q4 | 3.781781012951428 | 2.640805524240651 | 0.6176470588235294 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2026Q1 | 5.032730012569852 | 2.657120963131931 | 0.6470588235294118 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 2025Q1 | 7.688504213777702 | 4.419109970597145 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 2025Q2 | 6.4714002402089985 | 4.458692187415718 | 0.38235294117647056 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 2025Q3 | 5.08853744904713 | 2.9511480445583267 | 0.5588235294117647 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 2025Q4 | 3.781781012951428 | 2.640805524240651 | 0.6176470588235294 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | 2026Q1 | 5.032730012569852 | 2.657120963131931 | 0.6470588235294118 | 68 | f5874113b10d412b92d774d3f06e85120cbea29757c6591fc7c8809889945421 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 21. Worst Region·Industry

| policy_id | worst_type | worst_group | official_mae_pp | scored_rows | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | worst_quarter | 2025Q1 | 8.152018698099834 | 68 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | worst_quarter | 2025Q1 | 7.688504213777702 | 68 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | worst_quarter | 2025Q1 | 7.688504213777702 | 68 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | worst_quarter | 2025Q1 | 7.688504213777702 | 68 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | worst_region | 울산 | 10.312115061599018 | 20 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | worst_region | 제주 | 8.650938271598486 | 20 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | worst_region | 제주 | 8.650938271598486 | 20 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | worst_region | 제주 | 8.650938271598486 | 20 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | worst_industry | 건설업 | 13.847193570179725 | 85 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | worst_industry | 건설업 | 12.383626344256077 | 85 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | worst_industry | 건설업 | 12.383626344256077 | 85 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP3_G_pooled_robust_growth | worst_industry | 건설업 | 12.383626344256077 | 85 | e4c83a4c855423319c0e33534ab9ec306383c4b4890ca294d64435bc58d81eb4 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 22. Official Policy Selection

| development_metric_best | official_external_metric_best | gate_selected_policy | selection_status | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_national_bridge | QP1_G_national_growth_bridge | QP1_G_national_growth_bridge | provisional_official_growth_candidate_selected | False | False | fdf3ffc2081f916e7baa181dfc1a7fcc30bbfd3add3c2971ba8364654f1c8201 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 23. Origin Replay

| target_period | origin_id | origin_date | official_release_date | origin_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | F0 | 2025-01-01 | 2025-06-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | Q30 | 2025-04-30 | 2025-06-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | PRE_RELEASE | 2025-06-25 | 2025-06-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q2 | F0 | 2025-04-01 | 2025-09-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q2 | Q30 | 2025-07-30 | 2025-09-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q2 | PRE_RELEASE | 2025-09-25 | 2025-09-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q3 | F0 | 2025-07-01 | 2025-12-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q3 | Q30 | 2025-10-30 | 2025-12-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q3 | PRE_RELEASE | 2025-12-25 | 2025-12-26 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q4 | F0 | 2025-10-01 | 2026-03-30 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q4 | Q30 | 2026-01-30 | 2026-03-30 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q4 | PRE_RELEASE | 2026-03-29 | 2026-03-30 | independent_information_origin | 0035151ce8b6e97fe889726cced0c42c29949ca33d8d6854791172cc1d8c3744 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 24. Model Response Audit

| policy_id | target_period | prediction_hash | response_expected | response_observed | model_response_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 2025Q1 | bd58e4804844550fe455168c2c49c87c3ac8368efceb7d4634541b4996143e14 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q2 | 8e5dd86a062da29e1a6dbff91cca14a81518cf70e19c80fff2708c6c629094d7 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q3 | 62a0b1717aa1ffecbd44547109fbd9ca074819cda0f15c1db25c7d3afae612d1 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2025Q4 | 2e609b7fbf6b95a33cb667ede18f2d6889faa26d23c45980973c6eca25825394 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP0_G_seasonal_growth | 2026Q1 | bd58e4804844550fe455168c2c49c87c3ac8368efceb7d4634541b4996143e14 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q1 | 3be210832e830d51afe2d3ab61eb238f57050104988070d1b878cfe57dc00dd8 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q2 | 6ec6f441fa5aacf07763c6809fd0dc3a4ff6ead68f65a93f43de05adf286c9b5 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q3 | e3e4ba8a401c753a17645ec496a8975340cf8f34bb76853387069f24b1c7f8ad | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2025Q4 | bcff0864eabe288c2cb1e9abe30024342f89ecf7b05efd26ec8a28f89dba1947 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP1_G_national_growth_bridge | 2026Q1 | 3be210832e830d51afe2d3ab61eb238f57050104988070d1b878cfe57dc00dd8 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q1 | 3be210832e830d51afe2d3ab61eb238f57050104988070d1b878cfe57dc00dd8 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| QP2_G_indicator_growth_bridge | 2025Q2 | 6ec6f441fa5aacf07763c6809fd0dc3a4ff6ead68f65a93f43de05adf286c9b5 | false | false | expected_static_no_response | b935579838d2e8a18c4bed8a67629b173797c6f1ea1d0b04feea5befe62760b5 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 25. Revision Utility

| transition | evaluated_rows | revision_mae | harmful_revision_rate | direction_flip_rate | information_utilization_rate | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F0_to_Q30 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | expected_static_no_response | ac72462a50e46fc7c2e9f92c4bbf517d31270f60e61863c92e02f0b1b50179d0 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| Q30_to_PRE_RELEASE | 0 | 0.0 | 0.0 | 0.0 | 0.0 | expected_static_no_response | ac72462a50e46fc7c2e9f92c4bbf517d31270f60e61863c92e02f0b1b50179d0 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 26. Spatial Weight Sources

| source_id | source_status | quality_grade | source_counted | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_annual_grdp | active_benchmark | Q2 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| business_count_by_sigungu | pending_collection | Q3 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| employment_by_sigungu_industry | pending_collection | Q3 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| farmland_area_by_sigungu | pending_collection | Q3 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| factory_count_by_sigungu | pending_collection | Q3 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| construction_permit_area_by_sigungu | pending_collection | Q3 | Y | 2019c0322ee83334f8f1663d5aaa61acf48d3744a816eecc449864a70cd048a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 27. Annual Share Holdout

| spatial_policy_id | share_mae | gva_weighted_share_mae | evaluated_rows | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | 0.0055185247244303555 | 0.007167234232618469 | 8171 | baseline_selected_pending_structural_feature_activation | 0e9fc44187f632c8377e2b7acc6552e358dc99eaf27538aa88f63cc047d29aeb | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 28. Spatial Policy Selection

| selected_spatial_policy | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | baseline_retained_until_structural_holdout_improves | f76e0291ba5468f3e2001f6e7942dd54a6b769cf04fc91fcb996639b2429b4ee | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 29. Temporal Profile

TemporalProfile = AnnualChildGVA within-year quarterly share; official real parent growth is not imposed as a nominal hard constraint.

## 30. Profile Coverage

| indicator_profile_rows | fallback_profile_rows | indicator_profile_rate | fallback_profile_rate | selected_temporal_policy | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26904 | 20024 | 0.5733037845209683 | 0.4266962154790317 | TP7_when_indicator_available_else_TP1 | 312163ac46959c2b62d60bf33156005ae58ee039b9a61f0e9844dd25b4fc42a3 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 31. Temporal Profile Validation

| validation_id | status | metric_value | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| profile_nonnegative | pass | 1.0 | 81f674a5551e028a1540acac435fbeb1223cf35a326321ecb33c6d02bdf012b8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| annual_profile_sum | pass | 1.0 | 81f674a5551e028a1540acac435fbeb1223cf35a326321ecb33c6d02bdf012b8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| parent_growth_compatibility | diagnostic_only_price_basis_differs |  | 81f674a5551e028a1540acac435fbeb1223cf35a326321ecb33c6d02bdf012b8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 32. Real Growth Track

| target_period | region_name | official_industry_group | policy_id | alignment_status |
| --- | --- | --- | --- | --- |
| 2025Q1 | 서울 | GRDP | QP0_G_seasonal_growth | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP1_G_national_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP2_G_indicator_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | GRDP | QP3_G_pooled_robust_growth | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP0_G_seasonal_growth | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP1_G_national_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP2_G_indicator_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | 광업·제조업 | QP3_G_pooled_robust_growth | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP0_G_seasonal_growth | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP1_G_national_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP2_G_indicator_growth_bridge | aligned_primary |
| 2025Q1 | 서울 | 건설업 | QP3_G_pooled_robust_growth | aligned_primary |

## 33. Nominal Level Track

| source_region | sigungu_name | sector_name | period | development_status |
| --- | --- | --- | --- | --- |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2020Q1 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2020Q2 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2020Q3 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2020Q4 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2021Q1 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2021Q2 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2021Q3 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2021Q4 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2022Q1 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2022Q2 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2022Q3 | benchmark_consistent_quarterly_development_estimate |
| 강원특별자치도 | 춘천시 | 농업, 임업 및 어업 | 2022Q4 | benchmark_consistent_quarterly_development_estimate |

## 34. Deflator Feasibility

| deflator_candidate | deflator_status | track_merge_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| national_industry_or_regional_proxy_deflator | feasibility_only_not_merged | real_nominal_bridge_blocked | 22a283a1ed935922973bcc04a994e4891ee694d76e09e706472e341ecd2542a8 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 35. 2025 Locked Replay

| target_period | region_code | region_name | official_industry_group | policy_id | official_actual_growth_pct | predicted_growth_pct | absolute_error_pp | alignment_status | policy_reestimated_after_target | replay_role | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | 11 | 서울 | GRDP | QP0_G_seasonal_growth | 1.0 | 3.5621833404847703 | 2.5621833404847703 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | GRDP | QP1_G_national_growth_bridge | 1.0 | 3.5621833404847703 | 2.5621833404847703 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | GRDP | QP2_G_indicator_growth_bridge | 1.0 | 3.5621833404847703 | 2.5621833404847703 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | GRDP | QP3_G_pooled_robust_growth | 1.0 | 3.5621833404847703 | 2.5621833404847703 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 광업·제조업 | QP0_G_seasonal_growth | -4.3 | -2.813064732968873 | 1.4869352670311269 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 광업·제조업 | QP1_G_national_growth_bridge | -4.3 | 0.9945371904547806 | 5.294537190454781 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 광업·제조업 | QP2_G_indicator_growth_bridge | -4.3 | 0.9945371904547806 | 5.294537190454781 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 광업·제조업 | QP3_G_pooled_robust_growth | -4.3 | 0.9945371904547806 | 5.294537190454781 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 건설업 | QP0_G_seasonal_growth | -7.7 | 4.242995573262975 | 11.942995573262976 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 건설업 | QP1_G_national_growth_bridge | -7.7 | 4.242995573262975 | 11.942995573262976 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 건설업 | QP2_G_indicator_growth_bridge | -7.7 | 4.242995573262975 | 11.942995573262976 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |
| 2025Q1 | 11 | 서울 | 건설업 | QP3_G_pooled_robust_growth | -7.7 | 4.242995573262975 | 11.942995573262976 | aligned_primary | N | retrospective_external_evaluation | 2610aebe484afbef06238a221965ede2bdcc4e79ab4f154ae660b9b1633ea78b | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 36. 2026Q1 Official Parent

| target_period | region_name | official_industry_group | quarter_status |
| --- | --- | --- | --- |
| 2026Q1 | 서울 | GRDP | official_parent_observed_child_development_estimated |
| 2026Q1 | 서울 | 광업·제조업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 서울 | 건설업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 서울 | 서비스업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 부산 | GRDP | official_parent_observed_child_development_estimated |
| 2026Q1 | 부산 | 광업·제조업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 부산 | 건설업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 부산 | 서비스업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 대구 | GRDP | official_parent_observed_child_development_estimated |
| 2026Q1 | 대구 | 광업·제조업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 대구 | 건설업 | official_parent_observed_child_development_estimated |
| 2026Q1 | 대구 | 서비스업 | official_parent_observed_child_development_estimated |

## 37. 2026 Quarterly Output

| target_period | period | year | quarter | quarter_status | actual_used |
| --- | --- | --- | --- | --- | --- |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |
| 2026Q1 | 2026Q1 | 2026 | 1 | official_parent_observed_child_development_estimated | official_growth_only |

## 38. Prospective Holdout

| target_period | period | year | quarter | forecast_created_at | information_cutoff | official_expected_release_window | policy_id | prediction_measure | price_basis | configuration_hash | prediction_hash | prediction_rows | archive_status | one_shot_consumed | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q2 | 2026Q2 | 2026 | 2 | 2026-07-19T01:29:26+09:00 | 2026-07-19 | 2026-09 | QP1_G_national_growth_bridge | real_yoy_growth | real_growth_track | 4764f676888704de11d20ae4dece02468b4c0f34d417f05945fb387e7e76b3a6 | 9b51863976a0645146481f5ad66f69ab8375b50e17bab298a458d818b9599085 | 340 | frozen_waiting_first_release | False | e00acb8def7a8fc3eeefd39900de6b79b96a9d2bce74cadc2e245f35d796ebcc | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 39. Monthly Gate

monthly_primary_blocked

## 40. 불확실성

scenario_only: official target periods are only five first-release quarters.

## 41. Risk Queue

| risk | severity |
| --- | --- |
| official growth models use historical proxy growth as predictor source | medium |
| real-nominal bridge lacks validated deflator | medium |

## 42. 최종 정책

| development_metric_best | official_external_metric_best | gate_selected_policy | selection_status | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_national_bridge | QP1_G_national_growth_bridge | QP1_G_national_growth_bridge | provisional_official_growth_candidate_selected | False | False | fdf3ffc2081f916e7baa181dfc1a7fcc30bbfd3add3c2971ba8364654f1c8201 | 34b4323aa4218c9f394c4de0dc2beed15aa76ba6 | partial_statistics_estimation_phase23_gva | 2026-07-19T01:29:26+09:00 |

## 43. 한계

아직 주장할 수 없는 내용: Official level accuracy, statistical significance, production deployment, official statistics equivalence, and direct sigungu quarterly actual accuracy are not claimed.

## 44. 결론

Phase 23 completed official growth alignment and retained QP1_G_national_growth_bridge under status provisional_official_growth_candidate_selected.
