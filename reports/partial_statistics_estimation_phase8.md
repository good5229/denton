# Partial Statistics Estimation Phase 8

## 1. 실행 요약

최종 상태는 `blocked_stable_cube`다. KSIC 8→9는 복구했지만, KOSIS target raw source와 공식 공표일 evidence가 없어 primary stable cube와 challenger promotion은 차단했다.

| status | stable_cube | ksic8_9_recovered_rows | metric_mismatch_status | challenger_status | incumbent_retained | production_use | confirmatory_use | official_statistics_claim | holdout_status | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blocked_stable_cube | R4_sensitivity_cube_created_primary_blocked | 1273 | explained_population_difference | none | True | False | False | False | pending_new_sealed_official_vintage | 2026-07-18T14:23:35+09:00 |

## 2. Phase 7 기준선

| incumbent_source | incumbent_policy_hash | policy_ids | immutable | loaded_at |
| --- | --- | --- | --- | --- |
| Phase 7 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | ['P7_EST_NOWCAST_V1', 'P7_EMP_NOWCAST_V1', 'P7_EST_FORECAST_V1', 'P7_EMP_FORECAST_V1'] | True | 2026-07-18T14:23:35+09:00 |

## 3. Artifact 계보

| artifact_path | phase | artifact_role | row_count | schema_hash | sha256 | created_at | source_commit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| data/processed/partial_stats_phase5_grade_reassessment.csv | phase5 | csv_artifact | 2 | 84ed93366d4664bbe01a4293a6035a4399b9d59e4309bb51bfdfbcda635178f9 | b97e2076df414d48ced232cc77ca4856a2eb2570fcde73a499cb146a007bf1a4 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5_reproducibility_audit.csv | phase5 | csv_artifact | 9 | ab8b41ee0e4c3bbaa5042a87800f0ebcf85b02ecaf5e458282c0c4c1940c0366 | 83b6f638ec0e22207d9f9b4ca6bbf402c08f1ac8cbe5137e8d8d11203d5b5266 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_aggregate_accuracy.csv | phase5 | csv_artifact | 8160 | f5bf40eb90fbeffab6b64e09242255fc534e45183cd29f3f78fbfe96d0473ed2 | 1795230125436219a3401b407dce115ac417eab5bd66a89394eaa5437239f066 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_baseline_results.csv | phase5 | csv_artifact | 7680 | 84551fd5e05b8a0ea6086eb785de7a664aa60004d38dff61d63cbd072b1e96b8 | 06760b8fc9c1c0df7d07a702d2ca91e705ee50f8487f8b5df3e7eefb21b04ef1 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_execution_manifest.csv | phase5 | csv_artifact | 36 | 8fbd747eee946881d7f0031d08cf46debf4b36dd6096412b7efaddcb39ec3978 | fb6a6a3d01fe8d96986ce4d394223bdcee19376a0aae6e1f86351c36f3f6f997 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_experiment_manifest.json | phase5 | json_manifest |  |  | 87b79434507f8fcb4f9f2c3cdb296fc2174ca1adcea7c0924819117d27ce6eb5 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_extrapolation_audit.csv | phase5 | csv_artifact | 39672 | 164d961628e1dde4151cd96da4a506e7b2dc0437c996fe178db4f7c9a590893c | a8902c44bd9c51216c264de413a273a9c138abd25da1309d98f18712e4903a71 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_final_status.json | phase5 | json_manifest |  |  | 29a9d9398a85fce0afc8b5f02d994a5098be6bfc26db43bea87de5e6e5a62ef8 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_leakage_audit.csv | phase5 | csv_artifact | 480 | 4ae81c8c57bee82f2e21941e37348e1beb9739f2f726d27feab9953b776389ee | ac20b2ff7ba787ec3b06800d996bd44534143b55bda1b8bf1be3b983c0658b60 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_model_results.csv | phase5 | csv_artifact | 8640 | 84551fd5e05b8a0ea6086eb785de7a664aa60004d38dff61d63cbd072b1e96b8 | e121e8b3bb9ec353ddcf5be79f5de534a094fbde05a009b309a4959670ea5a45 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_negative_controls.csv | phase5 | csv_artifact | 2 | 410cc7a90e2966652cbd3f7c28c38e0aca43d3e952676fcd66d9ea21fe28e9c5 | 024726e0dc4372b422d3c9e4b3bd64c882edb11bc9af30c9c1a31021b25e1cd6 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |
| data/processed/partial_stats_phase5b_pipeline_registry.csv | phase5 | csv_artifact | 18 | 3b576ecb1d34cc0d3888c029f503f1922bd588611c1c8a2b22dd093ed2f60150 | c97f53dea3fb629d9b8504eccc1030d9e5a73feae4be677feba8b545e1bd5528 | 2026-07-18T14:23:35+09:00 | 9f0f509e0c747e22b7dfcb2c0c5051606d593bfe |

## 4. Phase 6·7 Metric 불일치

0.083/0.098과 0.290/0.259의 차이는 같은 모델의 실패가 아니라 평가 모집단 차이다. P1 nowcast와 horizon-level mixed support population이 섞여 있었다.

| target_name | phase6_nowcast_p1_wmape | phase6_horizon_nowcast_all_wmape | phase7_reproduced_p1_wmape | phase7_horizon_nowcast_all_wmape | judgement | explanation | blocks_new_model_comparison |
| --- | --- | --- | --- | --- | --- | --- | --- |
| establishments | 0.0830871221209108 | 0.29015286210642194 | 0.0830871221209108 | 0.29015286210642194 | explained_population_difference | 0.083/0.098 are P1 future-period nowcast rows; 0.290/0.259 are horizon-level rows pooling region and industry cold-start problems. | N |
| employees | 0.0978123896946449 | 0.2593879983466484 | 0.0978123896946449 | 0.2593879983466484 | explained_population_difference | 0.083/0.098 are P1 future-period nowcast rows; 0.290/0.259 are horizon-level rows pooling region and industry cold-start problems. | N |

## 5. 공식 Target Raw Source

| reference_year | raw_source_grade | raw_file | official_url | download_date | sha256 | row_count | schema_hash | ksic_version | region_version | release_metadata_status | artifact_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020,2021,2022,2023,2024 | R4 | data/processed/expanded_manufacturing_sigungu_ksic.csv | https://kosis.kr |  | f19c4920d0b2b17f62e7e432a59aee24781bc506320b3965f1f863c6f2840d41 | 92634 | 71d8a6b690ae0b205670b67a7bba266811f9f124ed3097a998bb888041284fbf | KSIC10_current_table_assumed | current KOSIS code/name derivative | missing_official_release_evidence | target_processed_derivative |
| 2021,2022,2023 | R5 | data/processed/partial_stats_cell_registry.csv |  |  | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 39672 | 0eefaa1e71872821e5a1166a49054c32a6b857f174528138c1c1264e9289e308 |  |  |  | phase6_target_cube_derivative |
|  | R1 | data/raw/9차개정 연계표.xls |  |  | 8d24032e78a37b84a1df799676af9b0d2f83260cd324ae202a1f13b1f5fe1c58 |  |  |  |  |  | official_ksic_crosswalk_raw_not_target |

## 6. Historical Year Inventory

| reference_year | raw_source_grade | raw_file | official_url | download_date | sha256 | row_count | schema_hash | ksic_version | region_version | release_metadata_status | artifact_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020,2021,2022,2023,2024 | R4 | data/processed/expanded_manufacturing_sigungu_ksic.csv | https://kosis.kr |  | f19c4920d0b2b17f62e7e432a59aee24781bc506320b3965f1f863c6f2840d41 | 92634 | 71d8a6b690ae0b205670b67a7bba266811f9f124ed3097a998bb888041284fbf | KSIC10_current_table_assumed | current KOSIS code/name derivative | missing_official_release_evidence | target_processed_derivative |
| 2021,2022,2023 | R5 | data/processed/partial_stats_cell_registry.csv |  |  | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 39672 | 0eefaa1e71872821e5a1166a49054c32a6b857f174528138c1c1264e9289e308 |  |  |  | phase6_target_cube_derivative |
|  | R1 | data/raw/9차개정 연계표.xls |  |  | 8d24032e78a37b84a1df799676af9b0d2f83260cd324ae202a1f13b1f5fe1c58 |  |  |  |  |  | official_ksic_crosswalk_raw_not_target |

## 7. KSIC 8→9 복구

기존 `ksic8_9_official_crosswalk.csv` 0행 문제는 `data/raw/9차개정 연계표.xls`의 `구신연계표` 시트를 파싱해 복구했다.

| old_version | old_code | old_name | new_version | new_code | new_name | relationship_type | official_note | source_sheet | source_row | deterministic_mapping | relation_raw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KSIC8 | 01110 | 곡물 및 기타 식량작물 재배업 | KSIC9 | 01110 | 곡물 및 기타 식량작물 재배업 | one_to_many | 곡물 및 기타 식량작물 재배 (야생 채취 제외) | 구신연계표 | 3 | N |  |
| KSIC8 | 01110 | 곡물 및 기타 식량작물 재배업 | KSIC9 | 02030 | 임산물 채취업 | many_to_many | 야생 곡물 및 기타 식량 작물 채취 | 구신연계표 | 4 | N | 7 |
| KSIC8 | 01121 | 채소작물 재배업 | KSIC9 | 01121 | 채소작물 재배업 | one_to_many | 채소작물 재배 (야생 채취 제외) | 구신연계표 | 5 | N |  |
| KSIC8 | 01121 | 채소작물 재배업 | KSIC9 | 02030 | 임산물 채취업 | many_to_many | 야생 채소작물 채취 | 구신연계표 | 6 | N | 7 |
| KSIC8 | 01122 | 화훼작물 재배업 | KSIC9 | 01122 | 화훼작물 재배업 | one_to_one |  | 구신연계표 | 7 | Y |  |
| KSIC8 | 01123 | 종자 및 묘목 생산업 | KSIC9 | 01123 | 종자 및 묘목 생산업 | one_to_one |  | 구신연계표 | 8 | Y |  |
| KSIC8 | 01131 | 과실작물 재배업 | KSIC9 | 01131 | 과실작물 재배업 | one_to_many | 과실작물 재배 (야생 채취 제외) | 구신연계표 | 9 | N |  |
| KSIC8 | 01131 | 과실작물 재배업 | KSIC9 | 02030 | 임산물 채취업 | many_to_many | 야생 과실작물 채취 | 구신연계표 | 10 | N | 7 |
| KSIC8 | 01132 | 음료용 및 향신용 작물 재배업 | KSIC9 | 01132 | 음료용 및 향신용 작물 재배업 | one_to_many | 음료용 및 향신용 작물 재배 (야생 채취 제외) | 구신연계표 | 11 | N |  |
| KSIC8 | 01132 | 음료용 및 향신용 작물 재배업 | KSIC9 | 02030 | 임산물 채취업 | many_to_many | 야생 음료용 및 향신용 작물 재배 채취 | 구신연계표 | 12 | N | 7 |
| KSIC8 | 01140 | 기타 작물 재배업 | KSIC9 | 01140 | 기타 작물 재배업 | one_to_many | 기타 작물 재배 (식용 기타작물 야생 채취 제외) | 구신연계표 | 13 | N |  |
| KSIC8 | 01140 | 기타 작물 재배업 | KSIC9 | 02030 | 임산물 채취업 | many_to_many | 야생 식용 기타 작물 채취 | 구신연계표 | 14 | N | 7 |

## 8. Stable Industry Universe

| stable_industry_code | stable_industry_name | stable_industry_level | mapping_determinism | year_coverage | primary_universe | selection_basis |
| --- | --- | --- | --- | --- | --- | --- |
| B05 | 석탄 원유 및 천연가스 광업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| B06 | 금속 광업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| B07 | 비금속광물 광업; 연료용 제외 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| B08 | 광업 지원 서비스업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C10 | 식료품 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C11 | 음료 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C12 | 담배 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C13 | 섬유제품 제조업; 의복제외 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C14 | 의복 의복 액세서리 및 모피제품 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C15 | 가죽 가방 및 신발 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C16 | 목재 및 나무제품 제조업; 가구 제외 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |
| C17 | 펄프 종이 및 종이제품 제조업 | middle | current_table_direct | 2020-2024 | Y | coverage_and_interpretability_before_model_performance |

## 9. Historical Region Crosswalk

| source_region_code | source_region_name | source_year | region_level | target_region_key | change_type | quality |
| --- | --- | --- | --- | --- | --- | --- |
| 26510 | 울주군 | 2020-2024 | sigungu | 26510 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 29010 | 세종특별자치시 | 2020-2024 | sigungu | 29010 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 32050 | 태백시 | 2020-2024 | sigungu | 32050 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 32070 | 삼척시 | 2020-2024 | sigungu | 32070 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 36570 | 화순군 | 2020-2024 | sigungu | 36570 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 37010 | 포항시 | 2020-2024 | sigungu | 37010 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 37012 | 북구 | 2020-2024 | sigungu | 37012 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 11240 | 송파구 | 2020-2024 | sigungu | 11240 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 25050 | 대덕구 | 2020-2024 | sigungu | 25050 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 31270 | 포천시 | 2020-2024 | sigungu | 31270 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 32530 | 영월군 | 2020-2024 | sigungu | 32530 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |
| 32550 | 정선군 | 2020-2024 | sigungu | 32550 | exact_code_current_derivative | R4_processed_code_stable_pending_raw_official_crosswalk |

## 10. Stable Region Universe

| target_region_key | stable_region_name | stable_region_universe | primary_universe | period_coverage | release_allowed | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 26510 | 울주군 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 29010 | 세종특별자치시 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 32050 | 태백시 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 32070 | 삼척시 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 36570 | 화순군 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 37010 | 포항시 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 37012 | 북구 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 11240 | 송파구 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 25050 | 대덕구 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 31270 | 포천시 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 32530 | 영월군 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |
| 32550 | 정선군 | UCode5_R4 | provisional | 2020-2024 | N | processed derivative only; raw KOSIS target provenance and historical boundary evidence incomplete |

## 11. 공식 공표일

| reference_year | preliminary_release_date | final_release_date | table_update_date | revision_date | metadata_source | release_confidence | prediction_track |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2015 |  |  |  |  | 101/DT_1KI1511_10 | unknown | blocked_primary |
| 2024 |  |  |  |  | 101/DT_1FS1101 | unknown | blocked_primary |
| 2021 |  |  |  |  | 101/DT_1FS1101 | unknown | blocked_primary |
| 2024 |  |  |  |  | 101/DT_1K52F08 | unknown | blocked_primary |
| 2024 |  |  |  |  | 101/DT_1K52F03 | unknown | blocked_primary |

## 12. Prediction Origin

| prediction_origin_id | origin_kind | prediction_origin_date | target_period | forecast_horizon | official_track_eligible |
| --- | --- | --- | --- | --- | --- |
| O1_nowcast_2021 | annual_pre_release_nowcast | 2021-12-31 | 2021 | nowcast | blocked_release_unknown |
| O2_one_year_ahead_2021 | one_year_ahead | 2020-12-31 | 2021 | one_year_ahead | blocked_release_unknown |
| O1_nowcast_2022 | annual_pre_release_nowcast | 2022-12-31 | 2022 | nowcast | blocked_release_unknown |
| O2_one_year_ahead_2022 | one_year_ahead | 2021-12-31 | 2022 | one_year_ahead | blocked_release_unknown |
| O1_nowcast_2023 | annual_pre_release_nowcast | 2023-12-31 | 2023 | nowcast | blocked_release_unknown |
| O2_one_year_ahead_2023 | one_year_ahead | 2022-12-31 | 2023 | one_year_ahead | blocked_release_unknown |
| O1_nowcast_2024 | annual_pre_release_nowcast | 2024-12-31 | 2024 | nowcast | blocked_release_unknown |
| O2_one_year_ahead_2024 | one_year_ahead | 2023-12-31 | 2024 | one_year_ahead | blocked_release_unknown |

## 13. Stable Cube

Stable Cube는 2020-2024 R4 processed derivative 기반 sensitivity cube로 생성했다. Primary cube는 R1-R3 raw source 확보 전까지 pass가 아니다.

| audit_id | issue_count | status | reason |
| --- | --- | --- | --- |
| duplicate_stable_key | 0 | pass |  |
| negative_values | 0 | pass |  |
| unknown_target_unit | 0 | pass |  |
| unresolved_region | 0 | pass |  |
| unresolved_industry | 0 | pass |  |
| missing_provenance | 0 | pass |  |
| future_eligibility_violation | 0 | pass |  |
| primary_source_grade_gate | 41808 | blocked_primary | target cube is built from R4 derivative for sensitivity; primary stable cube requires R1-R3 target raw source |

## 14. Canonical Baseline

| baseline_id | source_model | implementation | canonical | promotion_allowed |
| --- | --- | --- | --- | --- |
| B0_last_observation_level | PB0 | latest official value before origin | Y | incumbent_only |
| B1_damped_trend_0_25 | PB2 redesigned | damped one-sided median growth | Y | N_proposed_gate |
| B2_hierarchical_median_growth | new canonical | industry median growth fallback | Y | N_source_grade_blocked |
| B5_conservative_abstention | new canonical | not_estimable when support is low | Y | N_development_only |

## 15. 후보모델 구현

C1은 실제 count likelihood가 없어 구현하지 않았고 proxy 사용도 금지했다. C3만 sensitivity로 계산했지만 promotion 대상은 아니다.

| model_id | model_family | implementation_status | promotion_allowed | reason |
| --- | --- | --- | --- | --- |
| C1_hierarchical_growth_count_model | count_growth | not_implemented | N | no true NB/Poisson-Tweedie likelihood implemented in Phase 8 |
| C2_guardrailed_residual_correction | residual_correction | blocked | N | no R1-R3 prospective feature bundle |
| C3_hierarchical_shrinkage_growth | growth_shrinkage | implemented_sensitivity | N | evaluated only on R4 processed derivative stable cube |

## 16. Alias·Proxy·Fallback

| requested_model_id | executed_model_id | fallback_used | fallback_reason | support_class | available_features |
| --- | --- | --- | --- | --- | --- |
| C1_hierarchical_growth_count_model |  | N | excluded instead of proxying to Ridge | all | F0 |
| C2_guardrailed_residual_correction | B0_last_observation_level | Y | feature bundle blocked | all | F0 |
| C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | N |  | PS1_temporal | F0 |

## 17. Feature Bundle

| feature_bundle | description | status | promotion_allowed |
| --- | --- | --- | --- |
| F0 | lagged target only | sensitivity_only_R4 | N |
| F1 | population | blocked_vintage | N |
| F2 | structural activity | blocked_vintage | N |

## 18. Parent Constraint

| parent_id | status | hard_constraint_allowed | reason |
| --- | --- | --- | --- |
| C1_sido_section_parent | validation_only | N | seven employee parent mismatches remain unresolved and release timing incomplete |
| current_parent_total | rejected_primary | N | parent may be released after prediction origin |

## 19. Rolling-origin 결과

| target_name | forecast_horizon | target_period | model_id | policy_id | evaluation_population_id | metric_definition_id | wmape | mae | rmsle | actual_sum | prediction_sum | n | population_hash | source_grade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | B0_last_observation_level | P8_R4_sensitivity_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | B0_last_observation_level | P8_R4_sensitivity_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R4_sensitivity_only |
| employees | one_year_ahead_sensitivity | 2021 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P8_R4_sensitivity_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2021 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P8_R4_sensitivity_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R4_sensitivity_only |
| employees | one_year_ahead_sensitivity | 2021 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P8_R4_sensitivity_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2021 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P8_R4_sensitivity_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R4_sensitivity_only |
| employees | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | B0_last_observation_level | P8_R4_sensitivity_2022_employees | M_WMAPE_POOLED_ABS | 0.08525742381408671 | 107.15377599416271 | 0.35597963209250305 | 3444961.0 | 3425287.5 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | B0_last_observation_level | P8_R4_sensitivity_2022_establishments | M_WMAPE_POOLED_ABS | 0.07267019908188674 | 1.477092828016311 | 0.246144689261266 | 84739.0 | 84459.0 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R4_sensitivity_only |
| employees | one_year_ahead_sensitivity | 2022 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P8_R4_sensitivity_2022_employees | M_WMAPE_POOLED_ABS | 0.08509174640651165 | 106.94554826425494 | 0.3559969975519819 | 3444961.0 | 3432148.5928035094 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2022 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P8_R4_sensitivity_2022_establishments | M_WMAPE_POOLED_ABS | 0.07243270737510181 | 1.4722655769390145 | 0.24626183809181873 | 84739.0 | 84554.94939117199 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R4_sensitivity_only |
| employees | one_year_ahead_sensitivity | 2022 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P8_R4_sensitivity_2022_employees | M_WMAPE_POOLED_ABS | 0.08661404508968037 | 108.8588133477528 | 0.35699304363777884 | 3444961.0 | 3452731.8712140378 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R4_sensitivity_only |
| establishments | one_year_ahead_sensitivity | 2022 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P8_R4_sensitivity_2022_establishments | M_WMAPE_POOLED_ABS | 0.07245522256603017 | 1.472723220202166 | 0.24682786466399476 | 84739.0 | 84842.79756468798 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R4_sensitivity_only |

## 20. Nowcast

_No rows_

## 21. Forecast

| target_name | forecast_horizon | model_id | wmape | n | actual_sum |
| --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | B0_last_observation_level | 0.08464277982006257 | 10993 | 13803079.0 |
| employees | one_year_ahead_sensitivity | B1_damped_trend_0_25 | 0.0843735517608021 | 10993 | 13803079.0 |
| employees | one_year_ahead_sensitivity | B2_hierarchical_median_growth | 0.0846741549566692 | 10993 | 13803079.0 |
| employees | one_year_ahead_sensitivity | C3_hierarchical_shrinkage_growth | 0.08430086049122994 | 10993 | 13803079.0 |
| establishments | one_year_ahead_sensitivity | B0_last_observation_level | 0.07650941475729531 | 16757 | 339524.0 |
| establishments | one_year_ahead_sensitivity | B1_damped_trend_0_25 | 0.07643456855713704 | 16757 | 339524.0 |
| establishments | one_year_ahead_sensitivity | B2_hierarchical_median_growth | 0.07639434370936879 | 16757 | 339524.0 |
| establishments | one_year_ahead_sensitivity | C3_hierarchical_shrinkage_growth | 0.07639305170996402 | 16757 | 339524.0 |

## 22. 연도별 안정성

| target_name | target_period | model_id | wmape | n | actual_sum |
| --- | --- | --- | --- | --- | --- |
| employees | 2021 | B0_last_observation_level | 0.0886877814761173 | 2728 | 3403930.0 |
| employees | 2021 | B1_damped_trend_0_25 | 0.0886877814761173 | 2728 | 3403930.0 |
| employees | 2021 | B2_hierarchical_median_growth | 0.0886877814761173 | 2728 | 3403930.0 |
| employees | 2021 | C3_hierarchical_shrinkage_growth | 0.0886877814761173 | 2728 | 3403930.0 |
| employees | 2022 | B0_last_observation_level | 0.08525742381408671 | 2741 | 3444961.0 |
| employees | 2022 | B1_damped_trend_0_25 | 0.08509174640651165 | 2741 | 3444961.0 |
| employees | 2022 | B2_hierarchical_median_growth | 0.08661404508968037 | 2741 | 3444961.0 |
| employees | 2022 | C3_hierarchical_shrinkage_growth | 0.08525035379774953 | 2741 | 3444961.0 |
| employees | 2023 | B0_last_observation_level | 0.08181080250783883 | 2731 | 3421113.0 |
| employees | 2023 | B1_damped_trend_0_25 | 0.08183709565072947 | 2731 | 3421113.0 |
| employees | 2023 | B2_hierarchical_median_growth | 0.08306408490278158 | 2731 | 3421113.0 |
| employees | 2023 | C3_hierarchical_shrinkage_growth | 0.08212054789216747 | 2731 | 3421113.0 |

## 23. Region Cold-start

| support_scope | estimate_status | release_allowed | reason |
| --- | --- | --- | --- |
| region_cold_start | not_estimable | N | Phase 6 cold-start WMAPE too high; Phase 8 source grade blocked |

## 24. Industry Cold-start

| support_scope | estimate_status | release_allowed | reason |
| --- | --- | --- | --- |
| industry_cold_start | not_estimable | N | Phase 6 cold-start WMAPE too high; Phase 8 source grade blocked |

## 25. Selective Prediction

| support_scope | confidence_threshold | coverage | cell_balanced_wmape | status |
| --- | --- | --- | --- | --- |
| temporal | 0.8 |  |  | blocked_primary |
| cold_start | 0.8 | 0.0 |  | not_estimable |

## 26. Bootstrap

| bootstrap_iteration | target_name | selected_model | challenger_selected | full_refit_executed | reason |
| --- | --- | --- | --- | --- | --- |
| 0 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 0 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 1 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 1 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 2 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 2 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 3 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 3 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 4 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 4 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 5 | establishments | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |
| 5 | employees | P7_incumbent | N | N | primary stable cube blocked by R4 source grade and missing release evidence |

## 27. Placebo

| placebo_id | target_name | placebo_applicable | reason |
| --- | --- | --- | --- |
| region_permutation | establishments | N | no exogenous/residual challenger qualified |
| region_permutation | employees | N | no exogenous/residual challenger qualified |
| industry_permutation | establishments | N | no exogenous/residual challenger qualified |
| industry_permutation | employees | N | no exogenous/residual challenger qualified |
| time_shift | establishments | N | no exogenous/residual challenger qualified |
| time_shift | employees | N | no exogenous/residual challenger qualified |
| random_residual | establishments | N | no exogenous/residual challenger qualified |
| random_residual | employees | N | no exogenous/residual challenger qualified |

## 28. Material Degradation

| target_name | candidate | material_degradation | decision |
| --- | --- | --- | --- |
| establishments | C3_hierarchical_shrinkage_growth | not_evaluated_primary | no_challenger_qualified |
| employees | C3_hierarchical_shrinkage_growth | not_evaluated_primary | no_challenger_qualified |

## 29. 불확실성

| target_name | nominal_80 | empirical_80 | status |
| --- | --- | --- | --- |
| establishments | 0.8 |  | blocked_primary_stable_cube |
| employees | 0.8 |  | blocked_primary_stable_cube |

## 30. 사업체 Challenger 판정

| target_name | selected_policy | selection_count | selection_share | challenger_status |
| --- | --- | --- | --- | --- |
| establishments | P7_incumbent | 1000 | 1.0 | none |

## 31. 종사자 Challenger 판정

| target_name | selected_policy | selection_count | selection_share | challenger_status |
| --- | --- | --- | --- | --- |
| employees | P7_incumbent | 1000 | 1.0 | none |

## 32. Incumbent 유지 여부

| incumbent_source | incumbent_policy_hash | policy_ids | immutable | loaded_at |
| --- | --- | --- | --- | --- |
| Phase 7 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | ['P7_EST_NOWCAST_V1', 'P7_EMP_NOWCAST_V1', 'P7_EST_FORECAST_V1', 'P7_EMP_FORECAST_V1'] | True | 2026-07-18T14:23:35+09:00 |

## 33. 정책 동결

| challenger_status | candidate_policy_ids | freeze_allowed | reason | policy_hash |
| --- | --- | --- | --- | --- |
| none | ['P8_EST_CHALLENGER_V1', 'P8_EMP_CHALLENGER_V1'] | False | primary stable cube blocked; no Phase 8 challenger qualified | e73a4a2ae16e9269ba9d6cc72c435f16102cfe7f3f1ad8ad2d15944569da7818 |

## 34. 신규 Holdout

| holdout_id | table_id | period | sealed_status | confirmatory_eligible |
| --- | --- | --- | --- | --- |
| H2_next_unseen_vintage | 101/DT_1FS1101 | first official year not accessed during development | pending | pending_raw_seal |

## 35. Forecast Archive

| forecast_id | policy_id | created_at | prediction_origin | information_cutoff | target_period | target_name | region_key | industry_code | raw_prediction | final_prediction | lower_80 | upper_80 | lower_95 | upper_95 | support_class | estimate_status | fallback | input_hash | policy_hash | code_commit_hash | target_cube_hash | origin_registry_hash | feature_registry_hash | model_config_hash | run_id | seed | phase8_archive_role | phase8_input_hash | phase8_policy_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a76cc7d7dd1520921612e868e0ae91513df6a68a8b575ed48953f958d5822531 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | B07 | 6.0 | 6.0 | 4.199999999999999 | 8.8 | 3.0 | 11.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 9986304bea7d8767db47fcec4f8e9b197d71895a4ed723caabe7722d0fb118f9 | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | B07 | 113.0 | 113.0 | 79.1 | 147.9 | 56.5 | 171.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 29f6562a285bfee9831f53ca9033ca53b9212d8ec7d14364aa6afef0021b5c55 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C10 | 59.0 | 59.0 | 41.3 | 77.7 | 29.5 | 90.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 6635acb52c20a312851a2bfaa95ac1b6f0dcc0a12134735327b8067f9a111308 | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | C10 | 1468.0 | 1468.0 | 1027.6 | 1909.4 | 734.0 | 2204.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 3d5399d7a83f89282c14eceeb19273807f88b8bb8f9ff9255fb1cf132345065b | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C11 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 1abd6f2a381e4da5f27cb382461f86b17c7e36b262218909f7e000a619ca78f1 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C14 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 4b486e4dd2def8c18bb7222a8f282f62c6e67bdda13631218a0bc4cbe6cac206 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C16 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| e13bb87318f4de64b81bbf4b12ea89be9814653909a46403f3b29db4d2772cf5 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C19 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 083e1005d391d6cd28018b041342c14562e7cd136d89a93e4cb8917096713160 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C20 | 4.0 | 4.0 | 2.8 | 6.2 | 2.0 | 8.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| cede3d22d05f5d30605c07150fed3a238bb44cf150bd0961e8fea25c524ad62b | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | C20 | 119.0 | 119.0 | 83.3 | 155.70000000000002 | 59.5 | 180.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| 384357c0f6ab255e2362beb9a84f6b2ec79a9f8fec42cc9777ace2a9af0ff95f | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C21 | 2.0 | 2.0 | 1.4 | 3.6 | 1.0 | 5.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |
| b6a752c94ded6a474d864150ed81ccc9b461187e4a2702e400e53fad48558ced | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C22 | 6.0 | 6.0 | 4.199999999999999 | 8.8 | 3.0 | 11.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | incumbent_forecast_archive_preserved | 474db1abdf8ca29a7b3e34f64cb39a56f8a97c5551c260b1abe8c291621a12be | 8a5cea6bc29ac0424649020e55794ca62eebaa2dec1fef5778ced7bbda928e27 |

## 36. 사용자 개입 요청

| request_id | priority | blocked_workstream | official_source | official_url | table_id | required_years | required_dimensions | required_metrics | required_file | target_path | reason | automation_failure | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P8-RAW-001 | P1 | Raw Target Source / Stable Cube / Challenger Promotion | KOSIS 광업·제조업조사 | https://kosis.kr | 101/DT_1FS1101 | 2015 onward if officially available; at minimum raw 2020-2024 | sigungu × KSIC middle-level | 사업체수, 종사자수 | official raw CSV or API response manifest | data/raw/partial_stats_target/DT_1FS1101/<year>/ | processed derivative R4 cannot support primary stable cube or challenger promotion | no preserved official raw export in repository and network/manual KOSIS export not performed in this run | pending_user_or_future_collection |
| P8-REL-001 | P1 | Publication / Official Track | KOSIS release metadata or official survey press release | https://kosis.kr | 101/DT_1FS1101 | all target reference years used in rolling-origin | table-level metadata | release date/month and revision date if any | official metadata evidence or press-release PDF | data/raw/partial_stats_release/DT_1FS1101/ | approximation track cannot be primary evidence for prospective promotion | official release dates absent from local metadata | pending_user_or_future_collection |

## 37. 한계

## 38. 최종 결론

No Phase 8 challenger qualified. The Phase 7 transparent last-observation policy remains the frozen incumbent.
