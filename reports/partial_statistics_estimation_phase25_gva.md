# Partial Statistics Estimation Phase 25-GVA

## 1. 실행 요약

| metric | value |
| --- | --- |
| status | release_ledger_unqualified;indicator_join_integrity_repaired;origin_information_equivalent;qp2_r_blocked_no_R1_R3_source;spatial_challenger_blocked_common_years;qp1_frozen_until_2026Q2_one_shot;monthly_primary_blocked |
| target | GVA |
| target_unchanged | True |
| phase24_reproduction_status | pass |
| holdout_2026q2_event_status | waiting_first_release |
| archive_2026q2_integrity | pass_existing_archive_preserved |
| one_shot_2026q2_result | waiting_first_release |
| qp0_retrospective_mae_pp | 6.5221863720425555 |
| qp1_retrospective_mae_pp | 5.612590585711022 |
| canonical_series_count | 17 |
| unresolved_duplicate_count | 378 |
| many_to_many_join_count | 0 |
| join_row_inflation_rate | 0.0 |
| materialized_quarterly_source_count | 4 |
| r1_r3_qualified_source_count | 0 |
| independent_origin_count | 1 |
| responsive_origin_count | 0 |
| f0_eligible_observation_count | 0 |
| q30_eligible_observation_count | 0 |
| pre_release_eligible_observation_count | 0 |
| qp2_r_prediction_row_count | 340 |
| qp2_r_changed_prediction_row_count | 0 |
| revision_row_count | 0 |
| mean_revision_utility | not_scored |
| harmful_revision_rate | not_scored |
| qp2_fallback_rate | 1.0 |
| qp2_prospective_status | blocked_not_2026Q3_shadow_qualified |
| archive_2026q3_status | frozen_qp0_qp1_rows_qp2_diagnostic_fallback |
| electricity_spatial_source_status | materialized_but_holdout_blocked_insufficient_common_years |
| building_permit_source_status | materialized_pilot_not_holdout_qualified |
| factory_registry_source_status | materialized_snapshot_not_holdout_qualified |
| spatial_holdout_result | spatial_challenger_failed_or_blocked |
| selected_spatial_policy | SW0_last_annual_gva_share |
| temporal_policy_status | TP1_retained_TP7_not_validated |
| real_nominal_bridge_status | blocked |
| monthly_primary_status | blocked |
| production_use | False |
| official_statistics_claim | False |
| recommended_policy | QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot |
| claims_still_prohibited | QP2-R improvement, revision utility, spatial challenger superiority, TP7 superiority, real-nominal bridge, production use, official statistics equivalence |
| generated_at | 2026-07-19T08:23:57+09:00 |

## 2. 목표 불변 선언

| primary_target | official_quarterly_direct_target | quarterly_incumbent | prospective_primary_holdout | next_prospective_shadow_target | production_use | official_statistics_claim |
| --- | --- | --- | --- | --- | --- | --- |
| region_x_industry_x_period_GVA | sido_x_broad_industry_x_quarter_real_yoy_growth | QP1_G_national_growth_bridge_frozen | 2026Q2 | 2026Q3 | False | False |

## 3. Phase 24 재현

| policy_id | expected_mae_pp | observed_mae_pp | mae_abs_diff | expected_median_ae_pp | observed_median_ae_pp | expected_direction_accuracy | observed_direction_accuracy | scored_rows | reproduction_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 6.522186372 | 6.5221863720425555 | 4.25552926230921e-11 |  | 3.7273046727326093 |  | 0.5176470588235295 | 340 | pass | b05f2099f8d688f14f082dbeaacf877f90b69b9263075b31482d216f5bd754bd | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| QP1_G_national_growth_bridge | 5.6125905857 | 5.612590585711022 | 1.1022294188478554e-11 | 3.2897052348 | 3.289705234823889 | 0.5176470588 | 0.5176470588235295 | 340 | pass | b05f2099f8d688f14f082dbeaacf877f90b69b9263075b31482d216f5bd754bd | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 4. 현재 Holdout Event 상태

| target_period | event_status | archive_integrity | official_actual_used | one_shot_consumed | checked_at |
| --- | --- | --- | --- | --- | --- |
| 2026Q2 | waiting_first_release | pass_existing_archive_preserved | False | False | 2026-07-19T08:23:57+09:00 |

## 5. Series Grain Audit

| source_family | series_id | industry_code | measure_type | unit | seasonal_adjustment | price_basis | raw_rows | region_count | period_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| energy_exogenous_with_ecos_quarterly.csv | energy_exogenous_with_ecos_quarterly.csv/None/index_level/unknown_unit/TOTAL/original_or_unspecified/index_or_unspecified | TOTAL | index_level | unknown_unit | original_or_unspecified | index_or_unspecified | 46 | 1 | 46 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| mining_manufacturing_production_index | mining_manufacturing_production_index/T10/생산지수(원지수)/2020＝100/C/original_or_unspecified/index_or_unspecified | C | 생산지수(원지수) | 2020＝100 | original_or_unspecified | index_or_unspecified | 360 | 18 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| rolling_national_quarterly_gdp_real | rolling_national_quarterly_gdp_real/13103136275999/경제활동별 GDP 및 GNI(원계열 실질 분기 및 연간)/십억원/TOTAL/original_or_unspecified/real_or_constant | TOTAL | 경제활동별 GDP 및 GNI(원계열 실질 분기 및 연간) | 십억원 | original_or_unspecified | real_or_constant | 500 | 12 | 44 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/E/original_or_unspecified/real_or_constant | E | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/G/original_or_unspecified/real_or_constant | G | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/H/original_or_unspecified/real_or_constant | H | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/I/original_or_unspecified/real_or_constant | I | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/J/original_or_unspecified/real_or_constant | J | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/K/original_or_unspecified/real_or_constant | K | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/L/original_or_unspecified/real_or_constant | L | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/M/original_or_unspecified/real_or_constant | M | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | service_production_index/T2/불변지수/2020＝100/N/original_or_unspecified/real_or_constant | N | 불변지수 | 2020＝100 | original_or_unspecified | real_or_constant | 40 | 2 | 20 | ac411ea84a8d46ec9ec6e528d2fd13cb3a115a4427d7dbca6e2d2b5e89721dce | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 6. Duplicate·Revision Audit

| source_family | raw_rows | canonical_unique_rows | exact_duplicate_count | revision_count | unresolved_duplicate_count | primary_use | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| energy_exogenous_with_ecos_quarterly.csv | 500 | 46 | 122 | 0 | 378 | N | 2e311c890a0bbed0dc62638c5387274f91adb9e19d07a7b6b7292d975affe081 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| mining_manufacturing_production_index | 360 | 360 | 0 | 0 | 0 | N | 2e311c890a0bbed0dc62638c5387274f91adb9e19d07a7b6b7292d975affe081 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| rolling_national_quarterly_gdp_real | 500 | 500 | 0 | 0 | 0 | N | 2e311c890a0bbed0dc62638c5387274f91adb9e19d07a7b6b7292d975affe081 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index | 500 | 500 | 0 | 0 | 0 | N | 2e311c890a0bbed0dc62638c5387274f91adb9e19d07a7b6b7292d975affe081 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 7. Join Cardinality Audit

| join_id | regional_rows_before_join | rows_after_join | join_row_inflation_rate | many_to_many_join_count | national_match_failure_rate | join_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| regional_to_national_indicator | 1386 | 1386 | 0.0 | 0 | 0.7546897546897547 | pass | d8f70aeace122bcd52011ba67cf08070adda0753d6d433ad009642634d732148 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 8. Release Evidence Registry

| source_id | release_evidence_grade | evidence_description | primary_origin_allowed | shadow_allowed | exclusion_reason | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | R4 | documented_or_proxy_lag_only | N | Y | R1_R3_official_release_timestamp_not_materialized | ec9903c61d56c97636898b378699891b5da50c3360aa070729d09658376cffba | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| service_production_index.csv | R4 | documented_or_proxy_lag_only | N | Y | R1_R3_official_release_timestamp_not_materialized | ec9903c61d56c97636898b378699891b5da50c3360aa070729d09658376cffba | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| energy_exogenous_with_ecos_quarterly.csv | R4 | documented_or_proxy_lag_only | N | Y | R1_R3_official_release_timestamp_not_materialized | ec9903c61d56c97636898b378699891b5da50c3360aa070729d09658376cffba | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| rolling_national_quarterly_gdp_real.csv | R4 | documented_or_proxy_lag_only | N | Y | R1_R3_official_release_timestamp_not_materialized | ec9903c61d56c97636898b378699891b5da50c3360aa070729d09658376cffba | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 9. Qualified Source 현황

| source_id | release_evidence_grade | primary_origin_allowed | exclusion_reason |
| --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | R4 | N | R1_R3_official_release_timestamp_not_materialized |
| service_production_index.csv | R4 | N | R1_R3_official_release_timestamp_not_materialized |
| energy_exogenous_with_ecos_quarterly.csv | R4 | N | R1_R3_official_release_timestamp_not_materialized |
| rolling_national_quarterly_gdp_real.csv | R4 | N | R1_R3_official_release_timestamp_not_materialized |

## 10. Origin별 As-of Feature Store

| target_period | origin_id | eligible_source_count | eligible_observation_count | eligible_observation_hash | model_input_hash | expected_prediction_change | observed_prediction_change | origin_information_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | F0 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q1 | Q30 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q1 | PRE_RELEASE | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q2 | F0 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q2 | Q30 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q2 | PRE_RELEASE | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q3 | F0 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q3 | Q30 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q3 | PRE_RELEASE | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q4 | F0 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q4 | Q30 | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025Q4 | PRE_RELEASE | 0 | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | N | N | blocked_no_R1_R3_release_timestamp | ca7f9a109e4a29876cd06af1ae2584c2038cd3a19fc0d8038cc356681531f9c7 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 11. Regional Surprise 무결성

| join_id | regional_rows_before_join | rows_after_join | join_row_inflation_rate | many_to_many_join_count | national_match_failure_rate | join_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| regional_to_national_indicator | 1386 | 1386 | 0.0 | 0 | 0.7546897546897547 | pass | d8f70aeace122bcd52011ba67cf08070adda0753d6d433ad009642634d732148 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 12. QP2-R 반응성

| target_period | region_code | official_industry_group | policy_id | prediction_changed_from_qp1 | origin_responsive_status | fallback_reason |
| --- | --- | --- | --- | --- | --- | --- |
| 2025Q1 | 11 | GRDP | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 11 | 광업·제조업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 11 | 건설업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 11 | 서비스업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 21 | GRDP | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 21 | 광업·제조업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 21 | 건설업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 21 | 서비스업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 22 | GRDP | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 22 | 광업·제조업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 22 | 건설업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |
| 2025Q1 | 22 | 서비스업 | QP2_R_minimal_release_dated_regional_surprise | N | blocked_no_R1_R3_release_dated_sources | no_primary_qualified_release_dated_indicator |

## 13. Revision Utility

| revision_row_count | mean_revision_utility | median_revision_utility | harmful_revision_rate | direction_flip_rate | correct_direction_flip_rate | worst_region_revision_utility | worst_industry_revision_utility | fallback_rate | revision_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | not_scored | not_scored | not_scored | not_scored | not_scored | not_scored | not_scored | 1.0 | not_scored_no_changed_prediction | 7df0d2881f3111748a5afd8c25e98a90e628e965f3c9b830f4d96412f5157871 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 14. QP0·QP1 공식 회고성능

| policy_id | expected_mae_pp | observed_mae_pp | mae_abs_diff | expected_median_ae_pp | observed_median_ae_pp | expected_direction_accuracy | observed_direction_accuracy | scored_rows | reproduction_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP0_G_seasonal_growth | 6.522186372 | 6.5221863720425555 | 4.25552926230921e-11 |  | 3.7273046727326093 |  | 0.5176470588235295 | 340 | pass | b05f2099f8d688f14f082dbeaacf877f90b69b9263075b31482d216f5bd754bd | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| QP1_G_national_growth_bridge | 5.6125905857 | 5.612590585711022 | 1.1022294188478554e-11 | 3.2897052348 | 3.289705234823889 | 0.5176470588 | 0.5176470588235295 | 340 | pass | b05f2099f8d688f14f082dbeaacf877f90b69b9263075b31482d216f5bd754bd | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 15. 2026Q2 One-shot 결과 또는 대기상태

| target_period | one_shot_status | qp0_result | qp1_result | official_actual_used | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q2 | waiting_first_release | not_scored | not_scored | N | 268bff3e5442d3f35232b6f53599a58d68e1e9e93497c98eff63bf1da0a7f131 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 16. 2026Q3 Forecast Archive

| target_period | archive_id | policy_id | prediction_rows | official_actual_used | archive_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026Q3 | QP0_F0 | QP0_G_seasonal_growth | 68 | N | frozen_forecast_rows | 02c6d3c6254c7d79499660db9d34b40569f10435ce319de2b92ab95724a6f699 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2026Q3 | QP1_F0 | QP1_G_national_growth_bridge | 68 | N | frozen_forecast_rows | 02c6d3c6254c7d79499660db9d34b40569f10435ce319de2b92ab95724a6f699 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2026Q3 | QP2_R_F0 | QP2_R_minimal_release_dated_regional_surprise | 68 | N | diagnostic_fallback_not_shadow_qualified | 02c6d3c6254c7d79499660db9d34b40569f10435ce319de2b92ab95724a6f699 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 17. 전력사용량 공간 Feature

| year | sido_name | sigungu_name | sigungu_code | industrial_kwh | first_eligible_period | sido_industrial_kwh | electricity_spatial_share | source_status | holdout_eligible_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 | 강원도 | 강릉시 | 32030 | 789194671.0 | 202602 | 5749586575.0 | 0.1372611162046899 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 고성군 | 32400 | 59062163.0 | 202602 | 5749586575.0 | 0.010272419108673044 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 동해시 | 32040 | 1158827534.0 | 202602 | 5749586575.0 | 0.20154971472883684 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 삼척시 | 32070 | 974909040.0 | 202602 | 5749586575.0 | 0.16956158973917182 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 속초시 | 32060 | 75534224.0 | 202602 | 5749586575.0 | 0.013137331356733244 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 양구군 | 32380 | 19759474.0 | 202602 | 5749586575.0 | 0.0034366773579716033 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 양양군 | 32410 | 44365116.0 | 202602 | 5749586575.0 | 0.007716227144557781 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 영월군 | 32330 | 704735589.0 | 202602 | 5749586575.0 | 0.12257152402301204 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 원주시 | 32020 | 803615706.0 | 202602 | 5749586575.0 | 0.13976930263025042 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 인제군 | 32390 | 38721523.0 | 202602 | 5749586575.0 | 0.006734662135251003 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 정선군 | 32350 | 190317039.0 | 202602 | 5749586575.0 | 0.03310099543983299 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 2025 | 강원도 | 철원군 | 32360 | 60047589.0 | 202602 | 5749586575.0 | 0.010443809866451137 | materialized | blocked_insufficient_common_years_with_2020_2023_sigungu_gva | 752e7532d4fd681ea9a032160597abe7526ea4aade3a9740c49eb799b754030f | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 18. 건축인허가 공간 Feature

| sigungu_feature_key | observation_period | prediction_origin | feature_name | feature_value | first_eligible_period | source_version | source_status | event_date_status | holdout_eligible_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 부산광역시 해운대구 | 200006 |  | permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 200006 |  | permit_floor_area | 18.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 200006 |  | unknown_permit_area | 18.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 200006 |  | unknown_permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201703 |  | permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201703 |  | permit_floor_area | 28.28 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201703 |  | unknown_permit_area | 28.28 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201703 |  | unknown_permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201706 |  | permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201706 |  | permit_floor_area | 144.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201706 |  | unknown_permit_area | 144.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| 부산광역시 해운대구 | 201706 |  | unknown_permit_count | 1.0 |  | buildinghub_vintage_20260717 | materialized_pilot | event_dates_separated_in_source_table | blocked_no_first_eligible_period_and_no_common_validated_years | 0420008eb16580dbb697298420e7bf6136f8c1d5c1fee0c3b957d84d7552a980 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 19. 공장등록 공간 Feature

| source_id | sigungu_feature_key | observation_period | feature_name | feature_value | publication_date | source_vintage | first_eligible_period | feature_role | flow_feature_allowed | source_status | stock_flow_status | holdout_eligible_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | active_factory_count_snapshot | 452 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | manufacturing_factory_count_snapshot | 452 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | factory_employee_count_snapshot | 5614.0 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | factory_site_area_snapshot | 2515980.705 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | factory_building_area_snapshot | 797132.336 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | factory_manufacturing_area_snapshot | 538008.936 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | industrial_complex_factory_count_snapshot | 175 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | industrial_complex_factory_share | 0.38716814 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | composition | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 강릉시 | 2020 | factory_employee_per_establishment | 12.42035398 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | composition | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 고성군 | 2020 | active_factory_count_snapshot | 73 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 고성군 | 2020 | manufacturing_factory_count_snapshot | 73 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| data_go_kr_factory_full_snapshot_20200229_file | 강원특별자치도 고성군 | 2020 | factory_employee_count_snapshot | 716.0 | 2025_page_metadata_or_download_date | 15106170_20200229_download | 2021-12-31_or_source_publication_date | stock | N | materialized_snapshot | stock_only | blocked_publication_date_not_exact_or_common_years_insufficient | fcef3d684f170e683221a26aa97db42c02207a7ad27c478cd384396c424dd538 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 20. Annual Spatial Share Holdout

| policy_id | common_year_count | common_years | share_mae | gva_weighted_share_mae | rank_correlation | false_spatial_update_rate | holdout_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW_ELEC_industrial_electricity_share | 0 |  | not_scored | not_scored | not_scored | not_scored | blocked_insufficient_common_years | 6e40ab306b1e2c9e0627289d5f08d689dc2c6b51af1bebc5ef7016ba12e347bc | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |
| SW0_last_annual_gva_share | 4 | 2020,2021,2022,2023 | 0.0055185247244303555 | 0.007167234232618469 | not_scored | not_scored | baseline_retained | 6e40ab306b1e2c9e0627289d5f08d689dc2c6b51af1bebc5ef7016ba12e347bc | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 21. 선택된 Spatial 정책

| selected_spatial_policy | electricity_spatial_source_status | building_permit_source_status | factory_registry_source_status | spatial_holdout_result | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0_last_annual_gva_share | materialized_but_holdout_blocked_insufficient_common_years | materialized_pilot_not_holdout_qualified | materialized_snapshot_not_holdout_qualified | spatial_challenger_failed_or_blocked | SW0_retained | c94dd5b7bb1a11ccdf38f3f4ccea907a184dc3a43f178869f99ebf040384d2c8 | 2f11600189f9897330f871142b5648399ceb6784 | partial_statistics_estimation_phase25_gva | 2026-07-19T08:23:57+09:00 |

## 22. Temporal 상태

TP1 retained. TP7 remains unvalidated because coverage and accounting constraints are not predictive accuracy.

## 23. Real·Nominal Bridge 상태

blocked: direct regional-industry annual nominal/real validation pair is not materialized.

## 24. 월별 Primary 상태

monthly_primary_blocked

## 25. Risk Queue

| risk | severity |
| --- | --- |
| R1-R3 publication timestamps remain missing | high |
| electricity spatial feature common years do not overlap enough with annual GVA holdout | medium |

## 26. 최종 정책

| recommended_policy | production_use | official_statistics_claim |
| --- | --- | --- |
| QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot | False | False |

## 27. 아직 주장할 수 없는 내용

QP2-R improvement, revision utility, spatial challenger superiority, TP7 superiority, real-nominal bridge, production use, official statistics equivalence

## 28. 결론

Phase 25 repaired indicator grain and join integrity, preserved the 2026Q2 holdout, generated real 2026Q3 QP0/QP1 forecast rows, and kept QP2-R blocked because no R1-R3 release-dated regional indicator source is available.
