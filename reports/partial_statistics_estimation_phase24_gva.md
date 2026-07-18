# Partial Statistics Estimation Phase 24-GVA

## 1. 실행 요약

| metric | value |
| --- | --- |
| status | policy_equivalence_detected;unique_policy_registry_rebuilt;origin_responsive_candidate_blocked_source_release_dates;spatial_last_share_retained;temporal_profile_baseline_retained;real_nominal_bridge_blocked;quarterly_child_development_retained;monthly_primary_blocked |
| target | GVA |
| target_unchanged | True |
| superseded_invalid_artifact_count | 1 |
| qp1_qp2_qp3_equivalent | True |
| independent_parent_policy_count | 2 |
| qp1_frozen | True |
| materialized_quarterly_source_count | 4 |
| qualified_quarterly_source_count | 0 |
| f0_source_count | 0 |
| q30_source_count | 0 |
| pre_release_source_count | 0 |
| qp0_retrospective_mae_pp | 6.5221863720425555 |
| qp1_retrospective_mae_pp | 5.612590585711022 |
| qp2_r_development_status | blocked_no_primary_qualified_publication_dated_indicators |
| qp3_s_retrospective_shadow_mae_pp | 6.02501985307538 |
| qp4_c_consistency_status | diagnostic_only_growth_contribution_not_materialized_as_feature |
| official_direction_accuracy | 0.5176470588235295 |
| worst_quarter | 2025Q1 |
| worst_region | 울산 |
| worst_industry | 건설업 |
| independent_origin_count | 3 |
| responsive_origin_count | 0 |
| revision_utility | not_scored_no_changed_prediction |
| harmful_revision_rate | not_scored_no_changed_prediction |
| spatial_registered_source_count | 6 |
| spatial_materialized_source_count | 1 |
| annual_share_holdout_status | baseline_only_no_structural_challenger |
| selected_spatial_policy | SW0_last_annual_gva_share |
| indicator_profile_coverage | 0.5733037845209683 |
| indicator_profile_holdout_status | blocked_no_independent_temporal_actual |
| selected_temporal_policy | TP1_project_parent_proxy_profile |
| deflator_status | real_nominal_bridge_blocked |
| real_nominal_bridge_status | real_nominal_bridge_blocked |
| official_2026q1_parent_status | official_parent_observed |
| archive_2026q2_integrity | pass_existing_archive_preserved |
| shadow_2026q2_archive_status | not_frozen_blocked_no_primary_qualified_indicators |
| forecast_2026q3_status | registered_forecast_archive_template |
| monthly_primary_status | blocked |
| uncertainty_status | scenario_only |
| recommended_policy | QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot |
| production_use | False |
| official_statistics_claim | False |
| generated_at | 2026-07-19T08:06:41+09:00 |

## 2. 목표 불변 선언

| primary_target | official_quarterly_direct_target | official_growth_incumbent | prospective_primary_holdout | production_use | official_statistics_claim |
| --- | --- | --- | --- | --- | --- |
| 지역×산업×기간별 GVA | 시도×광역산업×분기 실질 YoY 성장률 | QP1_G_national_growth_bridge | 2026Q2 | False | False |

## 3. Phase 23 결과

Phase 23 aligned official real YoY growth targets, but QP1/QP2/QP3 produced identical predictions. Phase 24 treats that as policy equivalence, not as three independent wins.

## 4. Superseded Artifact Audit

| artifact_path | artifact_hash | invalid_row_count | invalid_reason | superseded_by | allowed_for_training | allowed_for_reporting | artifact_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data/processed/partial_stats_phase22_gva_quarterly_nowcast_2026.csv | 8c5c05404733974b5be78381c69a5102717946b0da4240f21d283011228935a1 | 15244 | period_target_or_year_quarter_mismatch | partial_stats_phase24_gva_quarterly_output_2026.parquet | False | error_history_only | superseded_invalid_period_key | b81f3fbd015c2e2d075704012660673c27ee0ac45300de1d0e34ab8ea72e0823 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| data/processed/partial_stats_phase22_gva_quarterly_replay_2025.csv | f2ee366313d0e3b2efd9affda136db812b8c877d06af4cd618d53b5fdc3fd4c7 | 0 | period_target_or_year_quarter_mismatch | partial_stats_phase24_gva_quarterly_output_2026.parquet | False | error_history_only | valid | b81f3fbd015c2e2d075704012660673c27ee0ac45300de1d0e34ab8ea72e0823 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 5. Model Identity Audit

| policy_id | source_code_path | function_name | feature_set | parameter_json | parameter_hash | model_object_hash | prediction_hash | fallback_policy | fallback_rate | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | scripts/run_partial_statistics_phase23_gva.py | phase23.formulas.QP0 | region_last_same_quarter_growth | {"frozen_after_phase23": true} | 7873d7ef467f23c756976138a8be58f7123be555ca8df7c4f0f732fb5577ba42 | 2fd61b7eafbdb8e52430ca25690d386ed853cedd5f69317ed1a8382265159fb9 | 80618b4b513822b4bfdfe276105a8e376450b8e1e63b91ffb1fbd0e365a85c1b |  | 0.0 | ebe77d818eec9ab4c9b25d2bebca432d55778c3d07bd48f32b7f829443423e35 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP1_G_national_growth_bridge | scripts/run_partial_statistics_phase23_gva.py | phase23.formulas.QP1 | national_growth_plus_shrunk_regional_differential | {"frozen_after_phase23": true} | b9e5b017db5c00980b0e74b2bfcf3e19e6cdc3c5572164b783b50a0c8a0a1593 | 83a0475aaa6d3a764e54482a7a46f50bc0c204660587ddf72ef695023a6672c8 | f76bc420b4d417d9384bafd03672a99041adb0c6c9e3b7f4cbd78ad19bb5c331 |  | 0.0 | ebe77d818eec9ab4c9b25d2bebca432d55778c3d07bd48f32b7f829443423e35 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP2_G_indicator_growth_bridge | scripts/run_partial_statistics_phase23_gva.py | phase23.formulas.QP2 | phase23_alias_national_growth_bridge_no_indicator_residual | {"frozen_after_phase23": true} | d451742f45dd53cf9d409cde08eecf27b0fc712fbf0c273fde1e50a196299c84 | 6de8587c77c34715efe2095fb34d39c318eea420de6638c411b8a8e4a28fe2d3 | f76bc420b4d417d9384bafd03672a99041adb0c6c9e3b7f4cbd78ad19bb5c331 | QP1_G_national_growth_bridge | 1.0 | ebe77d818eec9ab4c9b25d2bebca432d55778c3d07bd48f32b7f829443423e35 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP3_G_pooled_robust_growth | scripts/run_partial_statistics_phase23_gva.py | phase23.formulas.QP3 | phase23_alias_national_growth_bridge_no_pooled_fit | {"frozen_after_phase23": true} | d0b1f9d945a476d0d1c076fe09cbe36da08f36c8ef5ad2b326108089f4e4874d | 1452efe57b366d5aa18ef64261c02760b8122b96fd0c73c8790763dd985ff531 | f76bc420b4d417d9384bafd03672a99041adb0c6c9e3b7f4cbd78ad19bb5c331 | QP1_G_national_growth_bridge | 1.0 | ebe77d818eec9ab4c9b25d2bebca432d55778c3d07bd48f32b7f829443423e35 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 6. Policy Equivalence

| left_policy_id | right_policy_id | prediction_difference_rate | mean_absolute_prediction_difference | maximum_prediction_difference | direction_difference_rate | fallback_difference_rate | origin_response_difference_rate | equivalence_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | QP1_G_national_growth_bridge | 0.9411764705882353 | 1.9256352401166683 | 15.688584282393826 | 0.11470588235294117 | 0.0 | 0.0 | independent_policy | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP0_G_seasonal_growth | QP2_G_indicator_growth_bridge | 0.9411764705882353 | 1.9256352401166683 | 15.688584282393826 | 0.11470588235294117 | 1.0 | 0.0 | independent_policy | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP0_G_seasonal_growth | QP3_G_pooled_robust_growth | 0.9411764705882353 | 1.9256352401166683 | 15.688584282393826 | 0.11470588235294117 | 1.0 | 0.0 | independent_policy | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP1_G_national_growth_bridge | QP2_G_indicator_growth_bridge | 0.0 | 4.832735518956564e-17 | 8.881784197001252e-16 | 0.0 | 1.0 | 0.0 | alias_registration_error | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP1_G_national_growth_bridge | QP3_G_pooled_robust_growth | 0.0 | 4.832735518956564e-17 | 8.881784197001252e-16 | 0.0 | 1.0 | 0.0 | alias_registration_error | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP2_G_indicator_growth_bridge | QP3_G_pooled_robust_growth | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | alias_registration_error | 648fa6f0d0e6122e9c45283d8e800bcaa1825d398399bb0c9206c3a4ddeb8b0c | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 7. Quarterly Source Registry

| source_id | block | native_frequency | observation_level | region_level | industry_level | release_date | revision_policy | quarter_aggregation_method | target_mapping | primary_eligibility | input_hash | code_commit_hash | run_id | created_at | source_status | official_publication_date_status | qualified_for_primary_origin_responsive | first_eligible_origin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | production | quarterly_native | indicator | sido | industry_broad | documented_or_proxy_lag | latest_local_snapshot | index_average | C00,B00 | conservative | 98c11d6658a2fff0838d94209dde582189c3097496a7b11686d936e88ebbaaee | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | materialized | proxy_lag_not_primary_qualified | N | not_qualified_without_official_release_date |
| service_production_index.csv | service | quarterly_native | indicator | sido | industry_broad | documented_or_proxy_lag | latest_local_snapshot | index_average | G00-S00 | conservative | 98c11d6658a2fff0838d94209dde582189c3097496a7b11686d936e88ebbaaee | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | materialized | proxy_lag_not_primary_qualified | N | not_qualified_without_official_release_date |
| energy_exogenous_with_ecos_quarterly.csv | energy_price_fx | quarterly_native | indicator | national | energy_related | documented_or_proxy_lag | latest_local_snapshot | quarter_average | D00,C00 | conservative | 98c11d6658a2fff0838d94209dde582189c3097496a7b11686d936e88ebbaaee | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | materialized | proxy_lag_not_primary_qualified | N | not_qualified_without_official_release_date |
| rolling_national_quarterly_gdp_real.csv | national_gdp | quarterly_native | indicator | national | industry_broad | documented_or_proxy_lag | latest_local_snapshot | level | all | conservative | 98c11d6658a2fff0838d94209dde582189c3097496a7b11686d936e88ebbaaee | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | materialized | proxy_lag_not_primary_qualified | N | not_qualified_without_official_release_date |

## 8. Release Ledger

| source_id | native_frequency | release_date_rule | official_publication_date_status | first_eligible_origin | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | quarterly_native | documented_or_proxy_lag | proxy_lag_not_primary_qualified | not_qualified_without_official_release_date | 6b19e3cbed3c297ca9ffe372a5f7098ce4aee9cf32f67c5dc9a24a46ae5b6530 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| service_production_index.csv | quarterly_native | documented_or_proxy_lag | proxy_lag_not_primary_qualified | not_qualified_without_official_release_date | 6b19e3cbed3c297ca9ffe372a5f7098ce4aee9cf32f67c5dc9a24a46ae5b6530 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | quarterly_native | documented_or_proxy_lag | proxy_lag_not_primary_qualified | not_qualified_without_official_release_date | 6b19e3cbed3c297ca9ffe372a5f7098ce4aee9cf32f67c5dc9a24a46ae5b6530 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| rolling_national_quarterly_gdp_real.csv | quarterly_native | documented_or_proxy_lag | proxy_lag_not_primary_qualified | not_qualified_without_official_release_date | 6b19e3cbed3c297ca9ffe372a5f7098ce4aee9cf32f67c5dc9a24a46ae5b6530 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 9. As-of Feature Store

| origin_id | eligible_source_count | eligible_observation_count | eligible_source_set_hash | eligible_observation_hash | raw_feature_hash | transformed_feature_hash | model_input_hash | prediction_hash | asof_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F0 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | blocked_no_primary_qualified_publication_dates | f5ad8101ebec37c275f0ce84e8990a848d97a8adc1759751d376d0e5591acbc1 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | blocked_no_primary_qualified_publication_dates | f5ad8101ebec37c275f0ce84e8990a848d97a8adc1759751d376d0e5591acbc1 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| PRE_RELEASE | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | blocked_no_primary_qualified_publication_dates | f5ad8101ebec37c275f0ce84e8990a848d97a8adc1759751d376d0e5591acbc1 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 10. Regional Surprise Feature

| dataset | c1_id | c1_nm | c2_id | c2_nm | observation_period | value_num | national_indicator_value | regional_surprise | signal_available | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.885 | 93.484 | 22.40100000000001 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.885 | 101.034 | 14.850999999999999 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.885 | 99.937 | 15.948000000000008 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.473 | 93.484 | 21.989000000000004 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.473 | 101.034 | 14.438999999999993 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 115.473 | 99.937 | 15.536000000000001 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 117.737 | 93.484 | 24.253 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 117.737 | 101.034 | 16.70299999999999 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q1 | 117.737 | 99.937 | 17.799999999999997 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2019Q2 | 122.634 | 106.266 | 16.367999999999995 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2020Q1 | 96.3 | 96.9 | -0.6000000000000085 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| mining_manufacturing_production_index | 11 | 서울특별시 | C | 제조업 | 2020Q1 | 96.3 | 95.5 | 0.7999999999999972 | Y | 59ad39be9c44be509f7775a87b60c0c0bcba680100c296ac223dfc4545fe9356 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 11. QP0-G Baseline

| policy_id | evaluation_scope | mae_pp | median_ae_pp | direction_accuracy | scored_rows | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | official_retrospective | 6.5221863720425555 | 3.7273046727326093 | 0.5176470588235295 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 12. QP1-G Frozen Incumbent

| policy_id | evaluation_scope | mae_pp | median_ae_pp | direction_accuracy | scored_rows | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_G_national_growth_bridge | official_retrospective | 5.612590585711022 | 3.289705234823889 | 0.5176470588235295 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 13. QP2-R Responsive Bridge

| policy_id | evaluation_scope | mae_pp | median_ae_pp | direction_accuracy | scored_rows | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP2_R_origin_responsive_regional_surprise | blocked_primary_origin_responsive |  |  |  | 0 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 14. QP3-S Shrunk Bridge

| policy_id | evaluation_scope | mae_pp | median_ae_pp | direction_accuracy | scored_rows | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP3_S_shrunk_national_bridge | official_retrospective_shadow_no_retune | 6.02501985307538 | 3.553925194737878 | 0.5294117647058824 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 15. QP4-C Contribution Reconciliation

| policy_id | execution_status | total_contribution_residual | reconciliation_adjustment | growth_contribution_used_as_target | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP4_C_contribution_reconciled_growth | diagnostic_only_growth_contribution_not_materialized_as_feature |  |  | N | 32764da3be06fae020d9a15760c631d43c7972484d7eb35f275ef2fd1c5c52de | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 16. Direction·Magnitude Model

Direction and magnitude remain separated. No official-threshold tuning was performed on 2025Q1~2026Q1.

## 17. Worst-group Guardrail

| worst_quarter | worst_region | worst_industry | guardrail_status |
| --- | --- | --- | --- |
| 2025Q1 | 울산 | 건설업 | diagnostic_registered_no_router_promotion |

## 18. Official Retrospective Evaluation

| policy_id | evaluation_scope | mae_pp | median_ae_pp | direction_accuracy | scored_rows | production_use | official_statistics_claim | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | official_retrospective | 6.5221863720425555 | 3.7273046727326093 | 0.5176470588235295 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP1_G_national_growth_bridge | official_retrospective | 5.612590585711022 | 3.289705234823889 | 0.5176470588235295 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP3_S_shrunk_national_bridge | official_retrospective_shadow_no_retune | 6.02501985307538 | 3.553925194737878 | 0.5294117647058824 | 340 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP2_R_origin_responsive_regional_surprise | blocked_primary_origin_responsive |  |  |  | 0 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| QP4_C_contribution_reconciled_growth | diagnostic_only |  |  |  | 0 | False | False | 0845a13b06221195dd0cd465e44756b690635e57193905e39116e9f0e69fa76f | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 19. Origin Response

| origin_id | policy_id | response_expected | response_observed | prediction_hash | origin_response_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F0 | QP0_G_seasonal_growth | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| F0 | QP1_G_national_growth_bridge | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| F0 | QP2_R_origin_responsive_regional_surprise | True | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_response_missing | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| F0 | QP3_S_shrunk_national_bridge | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| F0 | QP4_C_contribution_reconciled_growth | True | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_response_missing | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | QP0_G_seasonal_growth | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | QP1_G_national_growth_bridge | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | QP2_R_origin_responsive_regional_surprise | True | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_response_missing | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | QP3_S_shrunk_national_bridge | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30 | QP4_C_contribution_reconciled_growth | True | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_response_missing | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| PRE_RELEASE | QP0_G_seasonal_growth | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| PRE_RELEASE | QP1_G_national_growth_bridge | False | False | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | expected_static_no_response | 05e1f96af8ccb830bef674c7e0865ade015e9d93f73ca10b8571ae55f8f75bda | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 20. Revision Utility

| transition | revision_rows | revision_utility | harmful_revision_rate | direction_flip_rate | information_utilization_rate | expected_response_failure_rate | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F0_to_Q30 | 0 |  |  |  | 0.0 | 1.0 | not_scored_no_changed_prediction | 9f6662974737935e43313b4146f2fb86348efc212052bbb53462a154b4deface | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| Q30_to_PRE_RELEASE | 0 |  |  |  | 0.0 | 1.0 | not_scored_no_changed_prediction | 9f6662974737935e43313b4146f2fb86348efc212052bbb53462a154b4deface | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 21. Spatial Source Materialization

| source_id | source_status | quality_grade | source_counted | input_hash | code_commit_hash | run_id | created_at | registered_counted | materialized_counted | qualified_counted | model_used_counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_annual_grdp | active_benchmark | Q2 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | Y | Y | Y |
| business_count_by_sigungu | pending_collection | Q3 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | N | N | N |
| employment_by_sigungu_industry | pending_collection | Q3 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | N | N | N |
| farmland_area_by_sigungu | pending_collection | Q3 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | N | N | N |
| factory_count_by_sigungu | pending_collection | Q3 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | N | N | N |
| construction_permit_area_by_sigungu | pending_collection | Q3 | Y | 59ea72d1b712b6489ce6b36b6876b00604a8526422b0b7c6d29c8a01ed6ffff0 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | Y | N | N | N |

## 22. Annual Spatial Share Holdout

| policy_id | share_mae | gva_weighted_share_mae | evaluated_rows | status | input_hash | code_commit_hash | run_id | created_at | holdout_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | 0.0055185247244303555 | 0.007167234232618469 | 8171 | baseline_selected_pending_structural_feature_activation | 34b04d467ce42405107b3f6ad63defd6bf1ccde1c5704427d07c55c6d43255a2 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 | baseline_only_no_structural_challenger |

## 23. Spatial Policy Selection

| selected_spatial_policy | selection_status | registered_source_count | materialized_source_count | qualified_source_count | model_used_source_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | spatial_last_share_retained | 6 | 1 | 1 | 1 | 657adb54468aedf77310bc296673354ad1cbc0d0c07c830dabdefb2cd4bb0fee | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 24. Temporal Profile Holdout

| temporal_policy_id | profile_mae | quarterly_growth_mae | turning_point_accuracy | year_boundary_discontinuity | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TP1_project_parent_proxy_profile | 0.0 |  |  |  | baseline_development_profile | 3ffb159764c0a608a3800a11fb10fbb3c0df40a3480d71bab8b8657415706726 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |
| TP7_indicator_available_else_TP1 |  |  |  |  | not_validated_against_independent_profile_target | 3ffb159764c0a608a3800a11fb10fbb3c0df40a3480d71bab8b8657415706726 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 25. Indicator·Fallback Comparison

| comparison_id | indicator_profile_coverage | indicator_cell_performance_delta | fallback_cell_performance_delta | comparison_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| indicator_vs_fallback | 0.5733037845209683 |  |  | blocked_no_independent_temporal_actual | 25a187055fdc5e15090c7eb67defb880ce10d140624670238889ac7e28311289 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 26. Temporal Policy Selection

| selected_temporal_policy | shadow_temporal_policy | selection_status | indicator_profile_coverage | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP1_project_parent_proxy_profile | TP7_indicator_available_else_TP1 | temporal_profile_baseline_retained | 0.5733037845209683 | f65ced7290e079c84afbd8640f12c66dce010d22db2e01fcaafd21027d2ca035 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 27. Deflator Feasibility

| candidate | materialized_rows | validation_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| annual_implicit_deflator | 0 | blocked_nominal_and_real_annual_pair_not_materialized | d3ba1aac5efd65084a90091d32b7e99a7339dcb1685619097e8474b7117ff5c7 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

| price_proxy | source_status | regional_industry_mapping | primary_eligibility | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| national_quarterly_gdp_deflator | materialized_proxy | fail_not_direct | N | a793020b3a907370d0f5487a932158428c201a938e906d7cc12e1f9cec4665a5 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 28. Real·Nominal Bridge

| bridge_status | reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- |
| real_nominal_bridge_blocked | direct regional industry deflator and annual real/nominal validation pair not materialized | 5df4cb5f264c74ecfd6f6dcf2784eb5ce3e0c77b6375ef5099d01d1424780741 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 29. 2026Q1 Official Parent

2026Q1 official parent real growth remains observed; nominal child output remains development estimate.

## 30. 2026Q2 Prospective Archive

| target_period | policy_id | archive_status | original_prediction_hash | current_prediction_hash | archive_immutable | integrity_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q2 | QP1_G_national_growth_bridge | frozen_waiting_first_release | 9b51863976a0645146481f5ad66f69ab8375b50e17bab298a458d818b9599085 | 9b51863976a0645146481f5ad66f69ab8375b50e17bab298a458d818b9599085 | True | pass_existing_archive_preserved | d7fd8f1f0b30db4771f9a6a8eac529eb590d72a02adad8d079dfc09b577be0ba | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 31. 2026Q3 Forecast Archive

| target_period | period | year | quarter | policy_id | forecast_status | official_actual_used | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q3 | 2026Q3 | 2026 | 3 | QP1_G_national_growth_bridge | registered_forecast_archive_template | N | bf4b51ebea1e0af649dcd5548091c62260a59061cf85ecfacad41d23cdd2e2c6 | 9ced0f4a99353bec901d6df843e2a1b666b0def9 | partial_statistics_estimation_phase24_gva | 2026-07-19T08:06:41+09:00 |

## 32. Monthly Gate

monthly_primary_blocked

## 33. 불확실성

scenario_only: QP1 is frozen until the 2026Q2 one-shot prospective evaluation.

## 34. Risk Queue

| risk | severity |
| --- | --- |
| publication-dated regional indicators are not yet qualified | high |
| QP2/QP3 Phase23 aliases inflated policy count | medium |

## 35. 최종 정책

| recommended_policy | production_use | official_statistics_claim |
| --- | --- | --- |
| QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot | False | False |

## 36. 한계

아직 주장할 수 없는 내용: QP2-R prospective improvement, origin revision utility, structural spatial-policy superiority, TP7 predictive superiority, real-nominal bridge validity, production deployment, official statistics equivalence.

## 37. 결론

Phase 24 corrected the policy-count inflation, preserved the 2026Q2 QP1 archive, and blocked unqualified responsive/structural/deflator claims until source publication dates and holdout evidence are available.
