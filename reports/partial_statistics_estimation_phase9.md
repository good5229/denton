# Partial Statistics Estimation Phase 9

## 1. 실행 요약

Phase 9 activated locally preserved KOSIS API response bodies as conditional official raw evidence. However `LST_CHN_DE` is only update evidence, so primary promotion remains blocked by release evidence.

| status | phase8_status_retained | raw_source_status | primary_stable_cube_rows | primary_activation | raw_r4_conflict_cells | forecast_archive_classification | incumbent_retained | challenger_status | production_use | confirmatory_use | official_statistics_claim | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blocked_release_evidence | blocked_stable_cube | activated_conditional_R2_official_api_body | 41808 | False | 0 | development_shadow_forecast | True | none_frozen | False | False | False | 2026-07-18T14:42:55+09:00 |

## 2. Phase 8 기준선

| phase8_status | primary_stable_cube | sensitivity_cube | ksic8_9_recovered_rows | phase7_incumbent_retained | phase8_challenger | production_use | confirmatory_use |
| --- | --- | --- | --- | --- | --- | --- | --- |
| blocked_stable_cube | blocked | R4 processed derivative | 1273 | true | none | false | false |

## 3. Threshold 및 Gate Registry

| threshold_id | threshold_value | threshold_origin | promotion_use |
| --- | --- | --- | --- |
| P7_POLICY_HASH | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | frozen_existing | Y_incumbent_identity_only |
| MATERIAL_DEGRADATION_ZERO_TOLERANCE | no_material_degradation_allowed | frozen_existing | Y_when_primary_track_exists |
| P9_RELEASE_CONFIDENCE_A_OR_B | official_first_release_date_or_month_required | proposed_gate | N_report_only_until_preregistered |
| RAW_R4_EXACT_RATE | descriptive | descriptive_only | N |

## 4. 2024 Forecast Archive Integrity

2024 archive is classified as `development_shadow_forecast`, not confirmatory. The target file existed locally before the physical forecast archive was created.

| archive_id | target_period | logical_prediction_origin | physical_forecast_created_at | target_first_local_presence | target_public_release | classification | confirmatory_eligible | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P7_2024_FORECAST_ARCHIVE | 2024 | 2023-12-31 or 2024-12-31 depending policy | 2026-07-18T14:06:27+09:00 | 2026-07-16T13:06:22+09:00 |  | development_shadow_forecast | N | 2024 target was already present in local processed development data before the archive file was physically created; first public release timing is also not proven |

## 5. Target 접근 Timeline

| event | artifact | event_time | time_semantics |
| --- | --- | --- | --- |
| target_processed_file_local_presence | data/processed/expanded_manufacturing_sigungu_ksic.csv | 2026-07-16T13:06:22+09:00 | physical_file_mtime |
| p7_forecast_archive_created | data/processed/partial_stats_phase7_forecast_archive.csv | 2026-07-18T14:06:27+09:00 | physical_file_mtime |
| p8_forecast_archive_created | data/processed/partial_stats_phase8_forecast_archive.csv | 2026-07-18T14:23:51+09:00 | physical_file_mtime |
| official_table_update_observed | raw field LST_CHN_DE | 2025-02-21,2026-01-13,2026-01-14,2026-01-15,2026-01-27,2026-02-26 | official_table_update_not_first_release |

## 6. Official Raw Source Inventory

| source_id | source_role | table_id | grain | targets | raw_files | raw_rows | min_reference_year | max_reference_year | source_grade | primary_raw_source_evidence | remaining_blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KOSIS_101_DT_1FS1101_JSON_CHUNKS | target_official_raw_api_body | 101/DT_1FS1101 | sigungu x mining_manufacturing_ksic x year | establishments,employees | 933 | 92634 | 2020 | 2024 | R2_official_api_body_header_missing | activated_conditionally | official_first_release_date_missing |
| R4_EXPANDED_MANUFACTURING_SIGUNGU_KSIC | sensitivity_reference_processed_derivative | 101/DT_1FS1101 | sigungu x mining_manufacturing_ksic x year | establishments,employees,value_added | 1 | 92634 |  |  | R4_processed_derivative | not_primary | none_for_diagnostic_only |

## 7. Raw Source Grade

| source_id | source_grade | grade_reason | eligible_for_primary_stable_cube | promotion_allowed |
| --- | --- | --- | --- | --- |
| KOSIS_101_DT_1FS1101_JSON_CHUNKS | R2_official_api_body_header_missing | official KOSIS API response bodies are preserved locally with ORG_ID, TBL_ID, C1, C2, ITM_ID, PRD_DE, DT, and LST_CHN_DE; response headers and explicit original request logs are absent | conditional_Y_raw_gate_pass_release_gate_blocked | N_until_release_evidence_A_or_B |
| R4_EXPANDED_MANUFACTURING_SIGUNGU_KSIC | R4_processed_derivative | processed derivative retained only for raw reconciliation and sensitivity | N | N |

## 8. 공식 공표일 Evidence

| reference_year | evidence_type | evidence_value | evidence_confidence | source_field | primary_release_evidence |
| --- | --- | --- | --- | --- | --- |
| 2020 | official_table_update_field | 2026-01-27 | C_update | LST_CHN_DE | N |
| 2021 | official_table_update_field | 2026-01-27 | C_update | LST_CHN_DE | N |
| 2022 | official_table_update_field | 2026-01-13,2026-01-14,2026-01-15 | C_update | LST_CHN_DE | N |
| 2023 | official_table_update_field | 2025-02-21 | C_update | LST_CHN_DE | N |
| 2024 | official_table_update_field | 2026-02-26 | C_update | LST_CHN_DE | N |

## 9. Revision History

| reference_year | revision_status | observed_update_dates | revision_policy |
| --- | --- | --- | --- |
| 2020 | update_field_observed_first_release_unknown | 2026-01-27 | block_confirmatory_and_primary_promotion |
| 2021 | update_field_observed_first_release_unknown | 2026-01-27 | block_confirmatory_and_primary_promotion |
| 2022 | update_field_observed_first_release_unknown | 2026-01-13,2026-01-14,2026-01-15 | block_confirmatory_and_primary_promotion |
| 2023 | update_field_observed_first_release_unknown | 2025-02-21 | block_confirmatory_and_primary_promotion |
| 2024 | update_field_observed_first_release_unknown | 2026-02-26 | block_confirmatory_and_primary_promotion |

## 10. Raw와 R4 Cell 대조

This comparison answers whether the R4 processed derivative preserved raw values. Conflicts are separately written to `partial_stats_phase9_raw_R4_conflicts.csv`.

| reference_year | stable_region_key | stable_industry_code | target_name | stable_region_name | stable_industry_name | raw_value | cell_status | r4_region_name | r4_industry_name | r4_value | comparison_status | abs_diff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 11010 | C13 | employees | 종로구 | 섬유제품 제조업; 의복제외 |  | suppressed_official | 종로구 | 섬유제품 제조업; 의복제외 |  | suppression_preserved |  |
| 2020 | 11010 | C13 | establishments | 종로구 | 섬유제품 제조업; 의복제외 | 2.0 | observed_official | 종로구 | 섬유제품 제조업; 의복제외 | 2.0 | exact_match | 0.0 |
| 2020 | 11010 | C14 | employees | 종로구 | 의복 의복 액세서리 및 모피제품 제조업 | 682.0 | observed_official | 종로구 | 의복 의복 액세서리 및 모피제품 제조업 | 682.0 | exact_match | 0.0 |
| 2020 | 11010 | C14 | establishments | 종로구 | 의복 의복 액세서리 및 모피제품 제조업 | 24.0 | observed_official | 종로구 | 의복 의복 액세서리 및 모피제품 제조업 | 24.0 | exact_match | 0.0 |
| 2020 | 11010 | C15 | employees | 종로구 | 가죽 가방 및 신발 제조업 |  | suppressed_official | 종로구 | 가죽 가방 및 신발 제조업 |  | suppression_preserved |  |
| 2020 | 11010 | C15 | establishments | 종로구 | 가죽 가방 및 신발 제조업 | 1.0 | observed_official | 종로구 | 가죽 가방 및 신발 제조업 | 1.0 | exact_match | 0.0 |
| 2020 | 11010 | C17 | employees | 종로구 | 펄프 종이 및 종이제품 제조업 | 71.0 | observed_official | 종로구 | 펄프 종이 및 종이제품 제조업 | 71.0 | exact_match | 0.0 |
| 2020 | 11010 | C17 | establishments | 종로구 | 펄프 종이 및 종이제품 제조업 | 5.0 | observed_official | 종로구 | 펄프 종이 및 종이제품 제조업 | 5.0 | exact_match | 0.0 |
| 2020 | 11010 | C18 | employees | 종로구 | 인쇄 및 기록매체 복제업 | 92.0 | observed_official | 종로구 | 인쇄 및 기록매체 복제업 | 92.0 | exact_match | 0.0 |
| 2020 | 11010 | C18 | establishments | 종로구 | 인쇄 및 기록매체 복제업 | 4.0 | observed_official | 종로구 | 인쇄 및 기록매체 복제업 | 4.0 | exact_match | 0.0 |
| 2020 | 11010 | C20 | employees | 종로구 | 화학물질 및 화학제품 제조업; 의약품 제외 | 160.0 | observed_official | 종로구 | 화학물질 및 화학제품 제조업; 의약품 제외 | 160.0 | exact_match | 0.0 |
| 2020 | 11010 | C20 | establishments | 종로구 | 화학물질 및 화학제품 제조업; 의약품 제외 | 4.0 | observed_official | 종로구 | 화학물질 및 화학제품 제조업; 의약품 제외 | 4.0 | exact_match | 0.0 |

## 11. Raw와 R4 Aggregate 대조

| reference_year | target_name | raw_total | r4_total | cells | exact_or_suppressed | conflicts | abs_total_diff |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | employees | 3371237.0 | 3371237.0 | 4147 | 4147 | 0 | 0.0 |
| 2020 | establishments | 81965.0 | 81965.0 | 4147 | 4147 | 0 | 0.0 |
| 2021 | employees | 3403930.0 | 3403930.0 | 4195 | 4195 | 0 | 0.0 |
| 2021 | establishments | 84069.0 | 84069.0 | 4195 | 4195 | 0 | 0.0 |
| 2022 | employees | 3444961.0 | 3444961.0 | 4169 | 4169 | 0 | 0.0 |
| 2022 | establishments | 84739.0 | 84739.0 | 4169 | 4169 | 0 | 0.0 |
| 2023 | employees | 3421113.0 | 3421113.0 | 4172 | 4172 | 0 | 0.0 |
| 2023 | establishments | 84392.0 | 84392.0 | 4172 | 4172 | 0 | 0.0 |
| 2024 | employees | 3533075.0 | 3533075.0 | 4221 | 4221 | 0 | 0.0 |
| 2024 | establishments | 86324.0 | 86324.0 | 4221 | 4221 | 0 | 0.0 |

## 12. Historical Region Evidence

| source_region_code | source_region_name | region_level | raw_table |
| --- | --- | --- | --- |
| 00 | 전국 | sido_or_total | 101/DT_1FS1101 |
| 29 | 세종특별자치시 | sido_or_total | 101/DT_1FS1101 |
| 32 | 강원특별자치도 | sido_or_total | 101/DT_1FS1101 |
| 36 | 전라남도 | sido_or_total | 101/DT_1FS1101 |
| 37 | 경상북도 | sido_or_total | 101/DT_1FS1101 |
| 26 | 울산광역시 | sido_or_total | 101/DT_1FS1101 |
| 26510 | 울주군 | sigungu | 101/DT_1FS1101 |
| 29010 | 세종특별자치시 | sigungu | 101/DT_1FS1101 |
| 32050 | 태백시 | sigungu | 101/DT_1FS1101 |
| 32070 | 삼척시 | sigungu | 101/DT_1FS1101 |
| 36570 | 화순군 | sigungu | 101/DT_1FS1101 |
| 37010 | 포항시 | sigungu | 101/DT_1FS1101 |

## 13. Stable Region Universe

| stable_region_key | stable_region_name | stable_region_universe | primary_universe | release_allowed |
| --- | --- | --- | --- | --- |
| 26510 | 울주군 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 29010 | 세종특별자치시 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 32050 | 태백시 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 32070 | 삼척시 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 36570 | 화순군 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 37010 | 포항시 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 37012 | 북구 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 11240 | 송파구 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 25050 | 대덕구 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 31270 | 포천시 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 32530 | 영월군 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |
| 32550 | 정선군 | UCode5_R2_raw | Y_raw_gate_conditional | N_release_evidence_blocked |

## 14. Raw KSIC Version

| source_industry_code | source_industry_name | source_industry_level | source_ksic_version | raw_table |
| --- | --- | --- | --- | --- |
| B0510 | 석탄 광업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B051 | 석탄 광업 | small | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B05 | 석탄 원유 및 천연가스 광업 | middle | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B0610 | 철 광업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B061 | 철 광업 | small | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B0620 | 비철금속 광업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B062 | 비철금속 광업 | small | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B06 | 금속 광업 | middle | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B0711 | 석회석 및 점토 광업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B0712 | 석재 쇄석 및 모래 자갈 채취업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B071 | 토사석 광업 | small | KSIC10_current_table_inferred | 101/DT_1FS1101 |
| B0721 | 화학용 및 비료원료용 광물 광업 | class | KSIC10_current_table_inferred | 101/DT_1FS1101 |

## 15. Stable Industry Universe

| stable_industry_code | stable_industry_name | stable_industry_level | primary_universe | release_allowed |
| --- | --- | --- | --- | --- |
| B05 | 석탄 원유 및 천연가스 광업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| B06 | 금속 광업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| B07 | 비금속광물 광업; 연료용 제외 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| B08 | 광업 지원 서비스업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C10 | 식료품 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C11 | 음료 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C12 | 담배 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C13 | 섬유제품 제조업; 의복제외 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C14 | 의복 의복 액세서리 및 모피제품 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C15 | 가죽 가방 및 신발 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C16 | 목재 및 나무제품 제조업; 가구 제외 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |
| C17 | 펄프 종이 및 종이제품 제조업 | middle | Y_raw_gate_conditional | N_release_evidence_blocked |

## 16. Primary Stable Cube

The cube is named primary because it is rebuilt from raw source bodies, but its registry keeps `primary_activation=false` until release evidence is acquired.

| stable_region_key | stable_region_name | stable_industry_code | stable_industry_name | reference_year | target_name | value | source_region_code | source_industry_code | source_ksic_version | source_file | source_hash | source_grade | release_confidence | first_eligible_origin | cell_status | last_changed_date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26510 | 울주군 | B05 | 석탄 원유 및 천연가스 광업 | 2020 | establishments | 1.0 | 26510 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 26510 | 울주군 | B05 | 석탄 원유 및 천연가스 광업 | 2021 | establishments | 1.0 | 26510 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 26510 | 울주군 | B05 | 석탄 원유 및 천연가스 광업 | 2022 | establishments | 1.0 | 26510 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-14 |
| 29010 | 세종특별자치시 | B05 | 석탄 원유 및 천연가스 광업 | 2023 | establishments | 1.0 | 29010 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2025-02-21 |
| 32050 | 태백시 | B05 | 석탄 원유 및 천연가스 광업 | 2020 | establishments | 5.0 | 32050 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 32050 | 태백시 | B05 | 석탄 원유 및 천연가스 광업 | 2021 | establishments | 6.0 | 32050 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 32050 | 태백시 | B05 | 석탄 원유 및 천연가스 광업 | 2022 | establishments | 4.0 | 32050 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-14 |
| 32050 | 태백시 | B05 | 석탄 원유 및 천연가스 광업 | 2023 | establishments | 2.0 | 32050 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2025-02-21 |
| 32050 | 태백시 | B05 | 석탄 원유 및 천연가스 광업 | 2024 | establishments | 1.0 | 32050 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-02-26 |
| 32070 | 삼척시 | B05 | 석탄 원유 및 천연가스 광업 | 2020 | establishments | 3.0 | 32070 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 32070 | 삼척시 | B05 | 석탄 원유 및 천연가스 광업 | 2021 | establishments | 3.0 | 32070 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-27 |
| 32070 | 삼척시 | B05 | 석탄 원유 및 천연가스 광업 | 2022 | establishments | 3.0 | 32070 | B05 | KSIC10_current_table_inferred | data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | 96b4beff4c4b100700f85f7440c6608bb1ba9c425e7fb890e6c7259484087706 | R2_official_api_body_header_missing | C_update_only |  | observed_official | 2026-01-14 |

## 17. Stable Cube Gate

| audit_id | issue_count | status | reason |
| --- | --- | --- | --- |
| duplicate_stable_key | 0 | pass |  |
| negative_values | 0 | pass |  |
| unknown_target_unit | 0 | pass |  |
| unresolved_region | 0 | pass |  |
| unresolved_industry | 0 | pass |  |
| missing_provenance | 0 | pass |  |
| raw_source_grade_gate | 0 | pass_conditional | official API response bodies exist, but headers/request manifests are reconstructed |
| release_date_gate | 41808 | fail | official first public release date is unavailable; LST_CHN_DE is update evidence only |
| first_eligible_origin_gate | 41808 | blocked_primary |  |

## 18. Prediction Origin

| reference_year | prediction_origin_kind | official_first_release_date | first_eligible_origin | eligibility_status | release_confidence | prediction_origin_id | prediction_origin_date | target_period |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | annual_pre_release_nowcast |  |  | blocked_release_evidence | C_update_only | P9_blocked_release_origin_2020 |  | 2020 |
| 2021 | annual_pre_release_nowcast |  |  | blocked_release_evidence | C_update_only | P9_blocked_release_origin_2021 |  | 2021 |
| 2022 | annual_pre_release_nowcast |  |  | blocked_release_evidence | C_update_only | P9_blocked_release_origin_2022 |  | 2022 |
| 2023 | annual_pre_release_nowcast |  |  | blocked_release_evidence | C_update_only | P9_blocked_release_origin_2023 |  | 2023 |
| 2024 | annual_pre_release_nowcast |  |  | blocked_release_evidence | C_update_only | P9_blocked_release_origin_2024 |  | 2024 |

## 19. Future Leakage Audit

| audit_id | status | contamination_class | confirmatory_allowed |
| --- | --- | --- | --- |
| local_target_presence_before_archive | fail_confirmatory | development_shadow_forecast | N |
| official_first_release_unknown | blocked_release_evidence | cannot_establish_pre_release_origin | N |

## 20. P7 Incumbent 재평가

| target_name | forecast_horizon | target_period | model_id | policy_id | evaluation_population_id | metric_definition_id | wmape | mae | rmsle | actual_sum | prediction_sum | n | population_hash | source_grade | evaluation_track | promotion_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | P7_EMP_FORECAST_V1 | P9_R2_release_blocked_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | P7_EST_FORECAST_V1 | P9_R2_release_blocked_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | P7_EMP_FORECAST_V1 | P9_R2_release_blocked_2022_employees | M_WMAPE_POOLED_ABS | 0.08525742381408671 | 107.15377599416271 | 0.35597963209250305 | 3444961.0 | 3425287.5 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | P7_EST_FORECAST_V1 | P9_R2_release_blocked_2022_establishments | M_WMAPE_POOLED_ABS | 0.07267019908188674 | 1.477092828016311 | 0.246144689261266 | 84739.0 | 84459.0 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2023 | B0_last_observation_level | P7_EMP_FORECAST_V1 | P9_R2_release_blocked_2023_employees | M_WMAPE_POOLED_ABS | 0.08181080250783883 | 102.48407176858294 | 0.3571830929159166 | 3421113.0 | 3458820.0 | 2731 | 3218b543283cb3d639bf704904d6d3ddc9bc8b91852f5f6e638ec5d43a98aeb9 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2023 | B0_last_observation_level | P7_EST_FORECAST_V1 | P9_R2_release_blocked_2023_establishments | M_WMAPE_POOLED_ABS | 0.07211584036401554 | 1.4587727708533078 | 0.24623932945919827 | 84392.0 | 85184.0 | 4172 | 7cb90e663500d8a2c0565514c4f8433efbe88d2afd66dade0313b7177b08053c | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2024 | B0_last_observation_level | P7_EMP_FORECAST_V1 | P9_R2_release_blocked_2024_employees | M_WMAPE_POOLED_ABS | 0.08281511148220742 | 104.75904045828858 | 0.3500022116759363 | 3533075.0 | 3463023.0 | 2793 | bda6dc540f8a90c0b1569157b7d8ec1f44e08e6f970735e9a6cdc9d2e9623e06 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2024 | B0_last_observation_level | P7_EST_FORECAST_V1 | P9_R2_release_blocked_2024_establishments | M_WMAPE_POOLED_ABS | 0.07881933181965618 | 1.6119402985074627 | 0.26893754783531354 | 86324.0 | 85122.0 | 4221 | a2502af2dca79dc81f4fec915cc4d384e40d485b75dedba36c71887a4c3151d8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |

## 21. Canonical Baseline

| target_name | forecast_horizon | target_period | model_id | policy_id | evaluation_population_id | metric_definition_id | wmape | mae | rmsle | actual_sum | prediction_sum | n | population_hash | source_grade | evaluation_track | promotion_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | B0_last_observation_level | P9_R2_release_blocked_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2021 | B0_last_observation_level | B0_last_observation_level | P9_R2_release_blocked_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2021 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P9_R2_release_blocked_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2021 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P9_R2_release_blocked_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2021 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P9_R2_release_blocked_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2021 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P9_R2_release_blocked_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | B0_last_observation_level | P9_R2_release_blocked_2022_employees | M_WMAPE_POOLED_ABS | 0.08525742381408671 | 107.15377599416271 | 0.35597963209250305 | 3444961.0 | 3425287.5 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2022 | B0_last_observation_level | B0_last_observation_level | P9_R2_release_blocked_2022_establishments | M_WMAPE_POOLED_ABS | 0.07267019908188674 | 1.477092828016311 | 0.246144689261266 | 84739.0 | 84459.0 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2022 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P9_R2_release_blocked_2022_employees | M_WMAPE_POOLED_ABS | 0.08509174640651165 | 106.94554826425494 | 0.3559969975519819 | 3444961.0 | 3432148.5928035094 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2022 | B1_damped_trend_0_25 | B1_damped_trend_0_25 | P9_R2_release_blocked_2022_establishments | M_WMAPE_POOLED_ABS | 0.07243270737510181 | 1.4722655769390145 | 0.24626183809181873 | 84739.0 | 84554.94939117199 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2022 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P9_R2_release_blocked_2022_employees | M_WMAPE_POOLED_ABS | 0.08661404508968037 | 108.8588133477528 | 0.35699304363777884 | 3444961.0 | 3452731.8712140378 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2022 | B2_hierarchical_median_growth | B2_hierarchical_median_growth | P9_R2_release_blocked_2022_establishments | M_WMAPE_POOLED_ABS | 0.07245522256603017 | 1.472723220202166 | 0.24682786466399476 | 84739.0 | 84842.79756468798 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |

## 22. C3 Shrinkage Candidate

| target_name | forecast_horizon | target_period | model_id | policy_id | evaluation_population_id | metric_definition_id | wmape | mae | rmsle | actual_sum | prediction_sum | n | population_hash | source_grade | evaluation_track | promotion_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | 2021 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2021_employees | M_WMAPE_POOLED_ABS | 0.0886877814761173 | 110.66239002932551 | 0.44926945578643473 | 3403930.0 | 3417512.0 | 2728 | 6b776a3e5c0333cc7865e6fb2642eb0a634e367c93ec113737767404bbaadf1a | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2021 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2021_establishments | M_WMAPE_POOLED_ABS | 0.08243228776362274 | 1.6519666269368296 | 0.2761894744193004 | 84069.0 | 82637.0 | 4195 | b7923bdf830e9861f6a85e08a43300ee90f5b0d8b55a4a017e2972d65efdf847 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2022 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2022_employees | M_WMAPE_POOLED_ABS | 0.08525035379774953 | 107.1448902114006 | 0.3561750739617477 | 3444961.0 | 3439009.685607019 | 2741 | af758f28b8c326961907f3360f7e61347c010ef450f8c8f57b21f67681127fd8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2022 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2022_establishments | M_WMAPE_POOLED_ABS | 0.07232853308025793 | 1.4701481325708745 | 0.24641570923011238 | 84739.0 | 84650.89878234398 | 4169 | 3783882b6af979e9ee0069a80cb946e54b4227f1df0a1e400bf28fada908e958 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2023 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2023_employees | M_WMAPE_POOLED_ABS | 0.08212054789216747 | 102.87208859795558 | 0.3573828880167678 | 3421113.0 | 3474705.3731514174 | 2731 | 3218b543283cb3d639bf704904d6d3ddc9bc8b91852f5f6e638ec5d43a98aeb9 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2023 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2023_establishments | M_WMAPE_POOLED_ABS | 0.07199205417631924 | 1.456268800586753 | 0.24621586331765694 | 84392.0 | 85223.27421129862 | 4172 | 7cb90e663500d8a2c0565514c4f8433efbe88d2afd66dade0313b7177b08053c | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | 2024 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2024_employees | M_WMAPE_POOLED_ABS | 0.08114475879888543 | 102.64608617736202 | 0.34977856961381365 | 3533075.0 | 3473474.016731199 | 2793 | bda6dc540f8a90c0b1569157b7d8ec1f44e08e6f970735e9a6cdc9d2e9623e06 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | 2024 | C3_hierarchical_shrinkage_growth | C3_hierarchical_shrinkage_growth | P9_R2_release_blocked_2024_establishments | M_WMAPE_POOLED_ABS | 0.07881933181965618 | 1.6119402985074627 | 0.26893754783531354 | 86324.0 | 85122.0 | 4221 | a2502af2dca79dc81f4fec915cc4d384e40d485b75dedba36c71887a4c3151d8 | R2_official_api_body_release_blocked | source_sensitivity_release_blocked | N |

## 23. Residual Candidate

| candidate | status | reason |
| --- | --- | --- |
| residual_candidate | not_evaluated | no promotable residual feature bundle in Phase 9 |

## 24. Feature Vintage

| source_file | endpoint | orgId | tblId | itmId | objL2 | startPrdDe | endPrdDe | format | request_params_reconstruction | api_key_persisted | traffic_guardrail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data/raw/expanded_manufacturing_sigungu_by_code/B0510_T01.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T01 | B0510 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B0510_T02.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T02 | B0510 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B0510_T06.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T06 | B0510 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B051_T01.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T01 | B051 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B051_T02.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T02 | B051 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B051_T06.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T06 | B051 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B05_T01.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T01 | B05 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B05_T02.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T02 | B05 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B05_T06.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T06 | B05 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B0610_T01.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T01 | B0610 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B0610_T02.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T02 | B0610 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |
| data/raw/expanded_manufacturing_sigungu_by_code/B0610_T06.json | https://kosis.kr/openapi/Param/statisticsParameterData.do | 101 | DT_1FS1101 | T06 | B0610 | 2020 | 2024 | json | inferred_without_api_key | N | local_raw_reuse_no_network_call |

## 25. Parent Constraint

| parent_constraint | status | reason |
| --- | --- | --- |
| current_parent_totals | not_used | release timing unavailable; avoid future leakage |

## 26. Rolling-origin 결과

| target_name | forecast_horizon | model_id | wmape | n | actual_sum | evaluation_track | promotion_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| employees | one_year_ahead_sensitivity | B0_last_observation_level | 0.08464277982006257 | 10993 | 13803079.0 | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | B1_damped_trend_0_25 | 0.0843735517608021 | 10993 | 13803079.0 | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | B2_hierarchical_median_growth | 0.0846741549566692 | 10993 | 13803079.0 | source_sensitivity_release_blocked | N |
| employees | one_year_ahead_sensitivity | C3_hierarchical_shrinkage_growth | 0.08430086049122994 | 10993 | 13803079.0 | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | B0_last_observation_level | 0.07650941475729531 | 16757 | 339524.0 | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | B1_damped_trend_0_25 | 0.07643456855713704 | 16757 | 339524.0 | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | B2_hierarchical_median_growth | 0.07639434370936879 | 16757 | 339524.0 | source_sensitivity_release_blocked | N |
| establishments | one_year_ahead_sensitivity | C3_hierarchical_shrinkage_growth | 0.07639305170996402 | 16757 | 339524.0 | source_sensitivity_release_blocked | N |

## 27. 연도별 안정성

| target_name | target_period | model_id | wmape | n | actual_sum | evaluation_track | promotion_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| employees | 2021 | B0_last_observation_level | 0.0886877814761173 | 2728 | 3403930.0 | source_sensitivity_release_blocked | N |
| employees | 2021 | B1_damped_trend_0_25 | 0.0886877814761173 | 2728 | 3403930.0 | source_sensitivity_release_blocked | N |
| employees | 2021 | B2_hierarchical_median_growth | 0.0886877814761173 | 2728 | 3403930.0 | source_sensitivity_release_blocked | N |
| employees | 2021 | C3_hierarchical_shrinkage_growth | 0.0886877814761173 | 2728 | 3403930.0 | source_sensitivity_release_blocked | N |
| employees | 2022 | B0_last_observation_level | 0.08525742381408671 | 2741 | 3444961.0 | source_sensitivity_release_blocked | N |
| employees | 2022 | B1_damped_trend_0_25 | 0.08509174640651165 | 2741 | 3444961.0 | source_sensitivity_release_blocked | N |
| employees | 2022 | B2_hierarchical_median_growth | 0.08661404508968037 | 2741 | 3444961.0 | source_sensitivity_release_blocked | N |
| employees | 2022 | C3_hierarchical_shrinkage_growth | 0.08525035379774953 | 2741 | 3444961.0 | source_sensitivity_release_blocked | N |
| employees | 2023 | B0_last_observation_level | 0.08181080250783883 | 2731 | 3421113.0 | source_sensitivity_release_blocked | N |
| employees | 2023 | B1_damped_trend_0_25 | 0.08183709565072947 | 2731 | 3421113.0 | source_sensitivity_release_blocked | N |
| employees | 2023 | B2_hierarchical_median_growth | 0.08306408490278158 | 2731 | 3421113.0 | source_sensitivity_release_blocked | N |
| employees | 2023 | C3_hierarchical_shrinkage_growth | 0.08212054789216747 | 2731 | 3421113.0 | source_sensitivity_release_blocked | N |

## 28. Material Degradation

| target_name | candidate | material_degradation | decision |
| --- | --- | --- | --- |
| establishments | C3_hierarchical_shrinkage_growth | not_promotable_release_gate_blocked | no_challenger_frozen |
| employees | C3_hierarchical_shrinkage_growth | not_promotable_release_gate_blocked | no_challenger_frozen |

## 29. Full-refit Bootstrap

| bootstrap_iteration | target_name | full_refit_executed | reason |
| --- | --- | --- | --- |
| 0 | establishments | N | primary release evidence blocked |
| 0 | employees | N | primary release evidence blocked |
| 1 | establishments | N | primary release evidence blocked |
| 1 | employees | N | primary release evidence blocked |
| 2 | establishments | N | primary release evidence blocked |
| 2 | employees | N | primary release evidence blocked |
| 3 | establishments | N | primary release evidence blocked |
| 3 | employees | N | primary release evidence blocked |
| 4 | establishments | N | primary release evidence blocked |
| 4 | employees | N | primary release evidence blocked |
| 5 | establishments | N | primary release evidence blocked |
| 5 | employees | N | primary release evidence blocked |

## 30. Placebo

| placebo_id | target_name | placebo_executed | reason |
| --- | --- | --- | --- |
| region_permutation | establishments | N | no promotable residual or exogenous challenger |
| region_permutation | employees | N | no promotable residual or exogenous challenger |
| industry_permutation | establishments | N | no promotable residual or exogenous challenger |
| industry_permutation | employees | N | no promotable residual or exogenous challenger |
| time_shift | establishments | N | no promotable residual or exogenous challenger |
| time_shift | employees | N | no promotable residual or exogenous challenger |

## 31. Uncertainty

| target_name | interval_method | numeric_release | reason |
| --- | --- | --- | --- |
| establishments | not_released | N | release gate blocked |
| employees | not_released | N | release gate blocked |

## 32. 2024 Development Shadow

| target_period | archive_rows | evaluation_status | join_status | reason |
| --- | --- | --- | --- | --- |
| 2024 | 200 | development_shadow_only | not_promoted_to_confirmatory | 2024 target was present before physical archive creation; raw official table exists but first release evidence is absent |

## 33. 사업체 Challenger 판정

| target_name | selected_policy | selection_share | selection_scope |
| --- | --- | --- | --- |
| establishments | P7_incumbent | 1.0 | blocked_primary_release_gate |

## 34. 종사자 Challenger 판정

| target_name | selected_policy | selection_share | selection_scope |
| --- | --- | --- | --- |
| employees | P7_incumbent | 1.0 | blocked_primary_release_gate |

## 35. Incumbent 유지 여부

| incumbent_source | incumbent_policy_hash | policy_ids | immutable | phase9_overwrite | loaded_at |
| --- | --- | --- | --- | --- | --- |
| Phase 7 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | ['P7_EST_NOWCAST_V1', 'P7_EMP_NOWCAST_V1', 'P7_EST_FORECAST_V1', 'P7_EMP_FORECAST_V1'] | True | False | 2026-07-18T14:42:55+09:00 |

## 36. Challenger 동결 여부

| challenger_status | freeze_allowed | reason | candidate_policy_ids |
| --- | --- | --- | --- |
| none_frozen | False | official raw body activated conditionally, but release evidence blocks primary evaluation and promotion | [] |

## 37. 다음 미사용 Holdout

| holdout_id | table_id | period | sealed_status | confirmatory_eligible |
| --- | --- | --- | --- | --- |
| H3_next_unseen_official_vintage | 101/DT_1FS1101 | first future official vintage not locally accessed | pending | pending |

## 38. Forecast Archive

| forecast_id | policy_id | created_at | prediction_origin | information_cutoff | target_period | target_name | region_key | industry_code | raw_prediction | final_prediction | lower_80 | upper_80 | lower_95 | upper_95 | support_class | estimate_status | fallback | input_hash | policy_hash | code_commit_hash | target_cube_hash | origin_registry_hash | feature_registry_hash | model_config_hash | run_id | seed | phase9_archive_role | confirmatory_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a76cc7d7dd1520921612e868e0ae91513df6a68a8b575ed48953f958d5822531 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | B07 | 6.0 | 6.0 | 4.199999999999999 | 8.8 | 3.0 | 11.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 9986304bea7d8767db47fcec4f8e9b197d71895a4ed723caabe7722d0fb118f9 | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | B07 | 113.0 | 113.0 | 79.1 | 147.9 | 56.5 | 171.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 29f6562a285bfee9831f53ca9033ca53b9212d8ec7d14364aa6afef0021b5c55 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C10 | 59.0 | 59.0 | 41.3 | 77.7 | 29.5 | 90.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 6635acb52c20a312851a2bfaa95ac1b6f0dcc0a12134735327b8067f9a111308 | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | C10 | 1468.0 | 1468.0 | 1027.6 | 1909.4 | 734.0 | 2204.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 3d5399d7a83f89282c14eceeb19273807f88b8bb8f9ff9255fb1cf132345065b | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C11 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 1abd6f2a381e4da5f27cb382461f86b17c7e36b262218909f7e000a619ca78f1 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C14 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 4b486e4dd2def8c18bb7222a8f282f62c6e67bdda13631218a0bc4cbe6cac206 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C16 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| e13bb87318f4de64b81bbf4b12ea89be9814653909a46403f3b29db4d2772cf5 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C19 | 1.0 | 1.0 | 0.7 | 2.3 | 0.5 | 3.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 083e1005d391d6cd28018b041342c14562e7cd136d89a93e4cb8917096713160 | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C20 | 4.0 | 4.0 | 2.8 | 6.2 | 2.0 | 8.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| cede3d22d05f5d30605c07150fed3a238bb44cf150bd0961e8fea25c524ad62b | P7_EMP_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | employees | 강원특별자치도 강릉시 | C20 | 119.0 | 119.0 | 83.3 | 155.70000000000002 | 59.5 | 180.5 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| 384357c0f6ab255e2362beb9a84f6b2ec79a9f8fec42cc9777ace2a9af0ff95f | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C21 | 2.0 | 2.0 | 1.4 | 3.6 | 1.0 | 5.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |
| b6a752c94ded6a474d864150ed81ccc9b461187e4a2702e400e53fad48558ced | P7_EST_FORECAST_V1 | 2026-07-18T14:05:55+09:00 | 2023-12-31 | 2023-12-31 | 2024 | establishments | 강원특별자치도 강릉시 | C22 | 6.0 | 6.0 | 4.199999999999999 | 8.8 | 3.0 | 11.0 | PS1_recent_temporal | forecast_archived_pending_official_release | N | cc58d8aa77dbf74fc1edc8f3ed003bc01f2634398ba8d239777855a1781c2af9 | aabd40f8c47957f65ddf84deae37523c9637ee074369391fe48ed164a268fc8d | 8ff0548c0e0d361fc6f47fda78e5d49daa4cc83e | fa3a6e7eb5aea38db4041bdc96806cd25b46b9edfe76016260ccad6b776ad358 | 1e0f53c87557bf52f2624d0340e865580fbbc23e5b40cfec27cf7634a837b39b | 3dc7ca45628f66794a70e90d9252e28e4149b974bfeb37a9e0d4fc7db2d6be56 | 82a59989c50fd751f425c00b6ceea09807506d482eaec5d8eec32783de016284 | partial_statistics_estimation_phase7 | 20260718 | preserved_development_shadow_archive | N |

## 39. 사용자 개입 요청

| request_id | priority | blocked_workstream | official_source | table_id | required_years | required_file | target_path | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P9-REL-001 | P1 | Primary Stable Cube / Confirmatory Evaluation / Challenger Promotion | KOSIS release metadata, MDIS notice, Statistics Korea press release, or archived table metadata | 101/DT_1FS1101 | 2020-2024 and future vintages | official first public release date/month and revision evidence | data/raw/partial_stats_release/DT_1FS1101/ | pending_user_or_future_collection |
| P9-RAW-META-001 | P2 | Raw source audit hardening | KOSIS OpenAPI request/response capture | 101/DT_1FS1101 | all local JSON chunks | original request manifests and response headers if available | data/raw/partial_stats_target/DT_1FS1101/request_manifest/ | optional_pending |

## 40. 한계

| limit_id | description |
| --- | --- |
| release_date_missing | official first public release date/month is not preserved locally; `LST_CHN_DE` is not enough for confirmatory timing |
| raw_header_missing | official API response bodies are preserved, but response headers and original request manifests are reconstructed |
| 2024_shadow_only | 2024 archive cannot be used as a true confirmatory holdout because local target presence predates archive creation |

## 41. 최종 결론

Phase 9 remains blocked on official release evidence. The raw-source and KSIC infrastructure are ready, but challenger promotion and confirmatory use are prohibited. The Phase 7 incumbent remains frozen.

| status | phase8_status_retained | raw_source_status | primary_stable_cube_rows | primary_activation | raw_r4_conflict_cells | forecast_archive_classification | incumbent_retained | challenger_status | production_use | confirmatory_use | official_statistics_claim | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blocked_release_evidence | blocked_stable_cube | activated_conditional_R2_official_api_body | 41808 | False | 0 | development_shadow_forecast | True | none_frozen | False | False | False | 2026-07-18T14:42:55+09:00 |
