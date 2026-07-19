# Partial Statistics Estimation Phase 27-GVA

## 1. 실행 요약

Phase 27은 서비스업생산 17개 시도 재수집, Strict/Pseudo track 분리, fine-grained target cube, 제한적 challenger 진단과 2026Q4 사전등록을 생성했다.

## 2. 목표·가격기준 불변 선언

`GVA` target은 유지했고 실질 성장률 track과 명목 level track은 hard reconcile하지 않았다.

## 3. Phase 26 재현

| check_id | expected | observed | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| phase26_final_status | semantic_recovered | semantic_recovered;release_event_current_update_only;qp2_fallback;historical_electricity_scored_not_promoted | pass | 283db461052415f7fc8c2629aa7a087d60ab1064045c3b5b1fb5eddd5ef4eed5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| qp1_mae | 5.612590585711022 | 5.612590585711022 | pass | 283db461052415f7fc8c2629aa7a087d60ab1064045c3b5b1fb5eddd5ef4eed5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| sw0_share_mae | 0.0055185247244303555 | 0.0055185247244303555 | pass | 283db461052415f7fc8c2629aa7a087d60ab1064045c3b5b1fb5eddd5ef4eed5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| sw0_weighted_share_mae | 0.007167234232618469 | 0.007167234232618469 | pass | 283db461052415f7fc8c2629aa7a087d60ab1064045c3b5b1fb5eddd5ef4eed5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

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

## 5. 2026Q3 Archive 상태

pass_existing_archives_preserved_new_asof_not_backdated

## 6. 서비스업생산 전체수집

| observed_region_count | expected_region_count | region_coverage_rate | observed_industry_count | expected_industry_count | industry_coverage_rate | observed_period_count | expected_period_count | period_coverage_rate | duplicate_key_count | expected_row_count_t1_t2 | observed_row_count | collection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | 17 | 1.0 | 14 | 14 | 1.0 | 20 | 20 | 1.0 | 0 | 9520 | 9520 | pass | 7d26ac87d6dc0d92aee643494f08204321fb9cdd5ff0f145e30ddde285cfde14 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 7. Historical Release Ledger

| release_event_id | source_id | series_scope | reference_period_start | reference_period_end | official_release_timestamp | evidence_grade | official_page_id_or_url | attachment_name | attachment_hash | page_hash | retrieved_at | revision_sequence | first_release_flag | mapping_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KOSIS_DT_1F02001_202605_latest_update_20260630 | mining_manufacturing_production_index.csv | DT_1F02001_latest_table_update_only | 2026-05 | 2026-05 | 2026-06-30T00:00:00+09:00 | R2 | https://kosis.kr/serviceInfo/newContrainDataDetail.do?boardIdx=1970002&boardOrgId=101 |  |  | web_search_snippet_20260719_recent_table_update | 2026-07-19T08:49:09+09:00 | latest_snapshot_update | unknown | materialized_current_update_not_historical_vintage | 9d2e34b953994936d3d341fb0e5eacdf1cec41702b37c222a67f31c86df01abb | 5d59719a70e25a1fa5240417411bfd9f77942bc9 | partial_statistics_estimation_phase26_gva | 2026-07-19T08:49:09+09:00 |

## 8. Strict·Pseudo Track 분리

| source_id | track | evidence_grade | reference_scope | use_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mining_manufacturing_production_index.csv | strict_asof | R2 | 2026-05 latest update only | eligible_only_for_matching_reference_period | fe556fa584cb09c772ad44948b9fa121d462e79f6353303f563386e4a3cf4419 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| service_production_index_full | pseudo_realtime_development | R4 | 2019Q1-2023Q4 current snapshot with chunk hashes | development_feature_only | bcc41df9e1403a3ae2857727b21a792c4a60b7cc1795b2ec54d78b58616db561 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| municipality_electricity_features_2021_2023 | pseudo_realtime_development | R4 | 2021-2023 proxy publication metadata | development_feature_only | bcc41df9e1403a3ae2857727b21a792c4a60b7cc1795b2ec54d78b58616db561 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| buildinghub_feature_table | pseudo_realtime_development | R5 | retrospective events | diagnostic_only | bcc41df9e1403a3ae2857727b21a792c4a60b7cc1795b2ec54d78b58616db561 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| factory_feature_table | pseudo_realtime_development | R5 | single snapshot | diagnostic_only | bcc41df9e1403a3ae2857727b21a792c4a60b7cc1795b2ec54d78b58616db561 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 9. Fine-grained Target Cube

| target_layer | target | frequency | direct_actual | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RQ1 | sido_x_broad_industry_real_yoy_growth | quarterly | Y | primary_parent | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NA1 | sigungu_x_ksic_section_nominal_gva | annual | Y | primary_spatial_industry_target | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NQ1 | sigungu_x_ksic_section_nominal_gva | quarterly | N | development_estimate | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NM1 | sigungu_x_ksic_section_nominal_gva | monthly | N | experimental_estimate | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NA2 | sigungu_x_ksic_division_nominal_gva | annual | conditional | shadow_target | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NQ2 | sigungu_x_ksic_division_nominal_gva | quarterly | N | restricted_shadow | 9474a365162758f0d7bc8d96be150fe22016c51695121736656a53276bd94ded | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 10. 지역 Crosswalk

| source_region | sigungu_code | sigungu_name | region_level | analysis_region_code | analysis_region_name | crosswalk_reason | effective_date | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32010 | 춘천시 | sigungu | 32010 | 춘천시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32020 | 원주시 | sigungu | 32020 | 원주시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32030 | 강릉시 | sigungu | 32030 | 강릉시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32040 | 동해시 | sigungu | 32040 | 동해시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32050 | 태백시 | sigungu | 32050 | 태백시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32060 | 속초시 | sigungu | 32060 | 속초시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32070 | 삼척시 | sigungu | 32070 | 삼척시 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32310 | 홍천군 | sigungu | 32310 | 홍천군 | special_self_governing_name_normalized | analysis_current | d0885dac0590c2e71c3f00f4909a6b80815b9359f37a5876e21b975f36662bfa | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 11. 산업 Crosswalk

| official_broad_industry | project_sector_code | KSIC_section | KSIC_division | mapping_weight | mapping_basis | valid_from | valid_to | additivity_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 농업, 임업 및 어업 | A00 | A |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 광업 | B00 | B |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 제조업 | C00 | C |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 전기, 가스, 증기 및 공기 조절 공급업 | D00 | D |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 문화 및 기타서비스업 | ERS | E,R,S |  | 1.0 | project_broad_bundle | 2020 |  | bundle_not_fine_additive | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 건설업 | F00 | F |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 도매 및 소매업 | G00 | G |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 운수 및 창고업 | H00 | H |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 숙박 및 음식점업 | I00 | I |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 정보통신업 | J00 | J |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 금융 및 보험업 | K00 | K |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 부동산업 | L00 | L |  | 1.0 | official_section | 2020 |  | additive_within_project_sector | 8dcadc9f600fdbe07f4dc395c830df817fcfb82c22cf4e37db70220de4dfafe5 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 12. 업종별 Feature Coverage

| observed_region_count | expected_region_count | region_coverage_rate | observed_industry_count | expected_industry_count | industry_coverage_rate | observed_period_count | expected_period_count | period_coverage_rate | duplicate_key_count | expected_row_count_t1_t2 | observed_row_count | collection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | 17 | 1.0 | 14 | 14 | 1.0 | 20 | 20 | 1.0 | 0 | 9520 | 9520 | pass | 7d26ac87d6dc0d92aee643494f08204321fb9cdd5ff0f145e30ddde285cfde14 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 13. Parent Residual Model

| policy_id | track | mae_pp | direction_accuracy | selection_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QP1_G_national_growth_bridge | strict_incumbent | 5.612590585711022 | 0.5176470588235295 | incumbent_frozen | 9ee8699ab82c34e2b1bb96a451b436f6b69604e41abac07a7a89e177dab3298b | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| PR1_diagnostic_capped_residual_beta_minus_0_5 | diagnostic_official_retrospective_not_promoted | 5.326203516245786 | 0.5176470588235295 | not_selected_official_target_visible | 9ee8699ab82c34e2b1bb96a451b436f6b69604e41abac07a7a89e177dab3298b | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 14. Direction Model

| policy_id | model_status | near_zero_threshold_pp | direction_accuracy | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PD1_direction_model | not_promoted_insufficient_strict_origin_response | 1.0 | not_scored_separately | d3aa2af44f23b7da6635eb2f336ab024cc4fd45fbb04594fa0067e520e815487 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 15. Dynamic Spatial Share

| policy_id | share_mae | weighted_share_mae | selection_status | guardrail | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SW0 | 0.0032263221529694533 | 0.007610836668433948 | incumbent_retained |  | 73fa54ae88232769b967ba69892a727b9041c61b30baefce79de4c5e3b1a198f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| SWD_Guarded_electricity_delta | 0.02684074227751501 | 0.06578053685177077 | failed_SW0_better | electricity_used_only_as_delta_feature | 73fa54ae88232769b967ba69892a727b9041c61b30baefce79de4c5e3b1a198f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 16. Industry Share

| policy_id | result | validation_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| IS0_previous_year_industry_share | baseline_retained | direct_annual_actual_available_at_KSIC_section | 96ec32f235360b4bac858c55e294b41ceab451b94789e7c03e621d5f113f0d40 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| IS1_employee_share_change | not_scored_feature_cube_incomplete | blocked | 96ec32f235360b4bac858c55e294b41ceab451b94789e7c03e621d5f113f0d40 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 17. Temporal Profile

| policy_id | result | component_gate | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| TP1_project_parent_proxy_profile | baseline_retained | annual_sum_recovery_pass | d9cbf4fa9005a78024cb858c0a1ee5ed1f58ce1262c2042d926793e128a54571 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| TP9_guarded_composite_denton | not_promoted_indicator_release_incomplete | not_scored | d9cbf4fa9005a78024cb858c0a1ee5ed1f58ce1262c2042d926793e128a54571 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 18. Hierarchical Reconciliation

| source_region | sigungu_code | sector_code | year | quarter_sum | annual_value | reconciliation_gap | adjustment_rate | binding_constraint | policy_id | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32010 | A00 | 2020 | 143868.0 | 143868.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | A00 | 2021 | 140847.0 | 140847.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | A00 | 2022 | 136327.0 | 136327.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | B00 | 2020 | 12528.0 | 12528.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | B00 | 2021 | 11440.0 | 11440.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | B00 | 2022 | 8682.0 | 8682.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | C00 | 2020 | 615831.0 | 615831.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | C00 | 2021 | 581420.0 | 581420.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | C00 | 2022 | 652799.0 | 652799.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 강원특별자치도 | 32010 | D00 | 2020 | 140177.0 | 140177.0 | 0.0 | 0.0 | annual=sum_quarters | proportional_reconciliation_preserved | 6f297576fe592364fe0f93ff10202df3fff4b04706cb69d25bb86a2f131ace7e | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 19. Rolling-origin 평가

| validation_origin | policy_scope | status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| train<=2019_validate2020 | spatial_share | available_for_SW0_only | 04d6c1335072aadb52af04cde03c4d4ba1b85bc0bf0d0bfc22c3d83d4c0f6760 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| train<=2020_validate2021 | spatial_share | available_for_SW0_and_electricity_delta_diagnostic | 04d6c1335072aadb52af04cde03c4d4ba1b85bc0bf0d0bfc22c3d83d4c0f6760 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| train<=2021_validate2022 | spatial_share | available_for_SW0_and_electricity_delta_diagnostic | 04d6c1335072aadb52af04cde03c4d4ba1b85bc0bf0d0bfc22c3d83d4c0f6760 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| train<=2022_validate2023 | spatial_share | available_for_SW0_and_electricity_delta_diagnostic | 04d6c1335072aadb52af04cde03c4d4ba1b85bc0bf0d0bfc22c3d83d4c0f6760 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 20. Leave-one-sido-out 평가

| validation_id | policy_id | result | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| leave_one_sido_out | SWD_Guarded_electricity_delta | not_promoted_SW0_better_and_publication_date_unqualified | 1cf865d2262c24052e754073e0144580a0093cc14f958230f6fdc0601a23939f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| county_only_holdout | SWD_Guarded_electricity_delta | not_scored_insufficient_region_type_labels | 1cf865d2262c24052e754073e0144580a0093cc14f958230f6fdc0601a23939f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 21. 지역별 성능

| group_type | group_id | metric | metric_value | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| region | service_full_collection | region_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 22. 시점별 성능

| group_type | group_id | metric | metric_value | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| period | service_full_collection | period_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 23. 업종별 성능

| group_type | group_id | metric | metric_value | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| industry | service_full_collection | industry_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| industry | SWD_electricity_delta | share_mae | 0.02684074227751501 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 24. Worst Group

| group_type | group_id | metric | metric_value | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| region | service_full_collection | region_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| period | service_full_collection | period_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| industry | service_full_collection | industry_coverage | 1.0 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| industry | SWD_electricity_delta | share_mae | 0.02684074227751501 | 564d4cf56315b0664a730e4132f03058fcfd0dce568c4ccbc914e20ad714005a | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 25. Material Degradation

| policy_id | material_degradation_count | degradation_reason | promotion_status | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SWD_Guarded_electricity_delta | 1 | share_mae_and_weighted_share_mae_worse_than_SW0 | blocked | 4077bba08fb72f7540e58c75359bf8316eb7a3876727147afcc3f30722f99136 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 26. 불확실성 Calibration

| interval | empirical_coverage | mean_interval_width_rate | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| 50 | not_scored_no_direct_quarterly_actual | 0.1 | 6140b20ba09d903e8794e8bf89e26aaac42e9899c6aef9d6934cb877e95894ba | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 80 | not_scored_no_direct_quarterly_actual | 0.2 | 6140b20ba09d903e8794e8bf89e26aaac42e9899c6aef9d6934cb877e95894ba | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| 95 | not_scored_no_direct_quarterly_actual | 0.3 | 6140b20ba09d903e8794e8bf89e26aaac42e9899c6aef9d6934cb877e95894ba | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 27. Fine-grained Output Coverage

| target_layer | row_count | region_count | industry_count | period_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NA1 | 11732 | 223 | 16 | 4 | c5dbf837fcd0c51351660ed65ae2e2d503c925912e26d02a0fb5516f4146d615 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NM1 | 140784 | 223 | 16 | 48 | c5dbf837fcd0c51351660ed65ae2e2d503c925912e26d02a0fb5516f4146d615 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| NQ1 | 46928 | 223 | 16 | 16 | c5dbf837fcd0c51351660ed65ae2e2d503c925912e26d02a0fb5516f4146d615 | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 28. 품질등급·Fallback

| quality_grade | fallback_level | row_count | input_hash | code_commit_hash | run_id | created_at |
| --- | --- | --- | --- | --- | --- | --- |
| A | direct_annual_anchor | 11732 | c6eee2ea42bf5cbfc2d7b2c555db1115c3b3499a7a10316875ec6c8672382a4f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| D | TP1_quarterly_development | 46928 | c6eee2ea42bf5cbfc2d7b2c555db1115c3b3499a7a10316875ec6c8672382a4f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |
| E | equal_month_experimental | 140784 | c6eee2ea42bf5cbfc2d7b2c555db1115c3b3499a7a10316875ec6c8672382a4f | 41bdc3cf91e580f34d9def806d7697ae0ea03cfd | partial_statistics_estimation_phase27_gva | 2026-07-19T09:10:45+09:00 |

## 29. 2026Q4 사전등록

{
  "target_period": "2026Q4",
  "origin_rule": "freeze_before_quarter_start_if_source_ledgers_ready",
  "created_at": "2026-07-19T09:10:45+09:00",
  "qp1_f0_policy": "QP1_G_national_growth_bridge_frozen_until_2026Q2_one_shot",
  "parent_challenger": "PR1_diagnostic_only_until_strict_origin_response",
  "spatial_policy": "SW0_last_annual_gva_share",
  "industry_policy": "IS0_previous_year_industry_share",
  "temporal_policy": "TP1_project_parent_proxy_profile",
  "reconciliation_policy": "proportional_reconciliation_preserved",
  "feature_release_rule": "strict_asof_R1_R3_only_for_prospective_promotion;R4_pseudo_development_only",
  "parameter_hash": "ec1a62473e205bfce1c29728d7b4315edab24928d5a1471bd2b975e76cfbe965",
  "official_actual_used": false,
  "archive_status": "preregistered_policy_skeleton_not_frozen_forecast"
}

## 30. 선택정책

Parent=QP1_G_national_growth_bridge, Spatial=SW0_last_annual_gva_share, Industry=IS0_previous_year_industry_share, Temporal=TP1_project_parent_proxy_profile.

## 31. 아직 주장할 수 없는 내용

parent challenger promotion, strict origin-responsive QP2, dynamic spatial superiority, industry challenger superiority, temporal challenger superiority, monthly direct actual accuracy, production use, official statistics equivalence

## 32. 결론

서비스 full collection은 통과했지만 historical strict release ledger와 challenger promotion gate가 부족해 incumbent 정책을 유지한다. Fine output은 개발/실험 추정으로만 사용한다.
