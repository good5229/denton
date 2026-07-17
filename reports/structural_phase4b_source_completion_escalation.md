# Structural Feature Phase 4B

## 1. 실행 요약

- 실행일: `2026-07-18T01:42:46+09:00`
- 목표: 최소 하나의 Structural Source를 ML-ready로 만들기 위한 source completion escalation.
- 결론: **ML 재개는 아직 차단**. 이번 Phase 4B에서도 모델 학습, Phase 5 preregistration, same-actual retuning은 실행하지 않았다.
- 생성 CSV: `54`개, JSON: `7`개. 모든 CSV는 CP949로 저장했다.

## 2. Phase 4 기준 상태

- Phase 4 기준선은 커밋된 산출물을 hash/row/schema 단위로 감사했다.
- KSIC Fine/Group/Division은 Phase 4 수치를 유지하며 Gate 완화는 하지 않았다.
- DAM_PDAN은 Point 1,451개로 diagnostic-only이다.

## 3. Source Completion 병렬경로

- Lane A/B: 사업체·고용 직접 시군구 source를 최우선으로 평가했다.
- Lane C/D: 공장 Aggregate와 Micro snapshot을 분리했다.
- Lane E: KSIC legacy mapping은 8→9 공식표 부재로 계속 차단했다.
- Lane G/H/I: 산업단지 workbook, API, 관할지역·allocation 경로를 분리했다.
- Spatial lane은 모델 성능을 보지 않고 검증 설계만 동결했다.

## 4. 사업체 Source Scorecard

| source_id | source_name | years_found | sigungu_region_count | industry_count | local_rows | historical_2021_2023_score | sigungu_coverage_score | official_publication_date_score | industry_top_level_score | definition_consistency_score | revision_history_score | free_approved_access_score | machine_readable_score | region_code_stability_score | total_score | primary_exclusion_reason | source_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kosis_national_establishment_census_sigungu_partial | 전국사업체조사/KOSIS 시군구 제조업·광업 세부 | 2021,2022,2023 | 262 | 29 | 34606 | 25 | 20 | 0 | 4 | 10 | 0 | 5 | 5 | 5 | 69 | full_industry_coverage_missing | development_only |
| kosis_national_establishment_census_sido_full | 전국사업체조사/KOSIS 시도×산업대분류 | 2021,2022,2023 | 17 | 19 | 3230 | 25 | 10 | 0 | 10 | 10 | 0 | 5 | 5 | 5 | 65 | sigungu_coverage_missing | development_only |
| economic_census_emd_2015 | 경제총조사 2015 읍면동×산업대분류 |  | 0 | 0 | 9620 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 10 | no_2021_2023_common_period | development_only |
| small_business_store_stock | 소상공인시장진흥공단 상가(상권)정보 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | historical_vintage_incomplete | blocked_source_missing |
| employment_insurance_workplaces | 고용보험 사업장·피보험자 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | local_source_missing | blocked_source_missing |

## 5. 고용 Source Scorecard

| source_id | source_name | years_found | sigungu_region_count | industry_count | local_rows | historical_2021_2023_score | sigungu_coverage_score | official_publication_date_score | industry_top_level_score | definition_consistency_score | revision_history_score | free_approved_access_score | machine_readable_score | region_code_stability_score | total_score | primary_exclusion_reason | source_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kosis_national_establishment_census_sigungu_partial | 전국사업체조사/KOSIS 시군구 제조업·광업 세부 | 2021,2022,2023 | 262 | 29 | 34606 | 25 | 20 | 0 | 4 | 10 | 0 | 5 | 5 | 5 | 69 | full_industry_coverage_missing | development_only |
| kosis_national_establishment_census_sido_full | 전국사업체조사/KOSIS 시도×산업대분류 | 2021,2022,2023 | 17 | 19 | 3230 | 25 | 10 | 0 | 10 | 10 | 0 | 5 | 5 | 5 | 65 | sigungu_coverage_missing | development_only |
| economic_census_emd_2015 | 경제총조사 2015 읍면동×산업대분류 |  | 0 | 0 | 9620 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 10 | no_2021_2023_common_period | development_only |
| small_employment_store_stock | 소상공인시장진흥공단 상가(상권)정보 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | historical_vintage_incomplete | blocked_source_missing |
| employment_insurance_workplaces | 고용보험 사업장·피보험자 |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | local_source_missing | blocked_source_missing |

## 6. KOSIS Table Inventory

- 로컬 mart 기준 `source_dataset × table × area × industry × metric` inventory를 구성했다.
- 시도×전산업 자료는 존재하지만 시군구×전산업 2021~2023과 공식 공표일을 동시에 만족하는 source는 아직 없다.

## 7. 전 산업 Historical Coverage

| source_dataset | target_years_found | period_coverage_pass | max_sigungu_region_count | max_industry_count | full_industry_coverage_pass | official_actual_unmatched_regions | gate_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| emd_economic_census_2015 |  | N | 0 | 0 | N | not_tested | blocked_publication_or_coverage |
| manufacturing_mining_sigungu_ksic | 2021,2022,2023 | Y | 262 | 311 | N | not_tested | blocked_publication_or_coverage |
| sido_industry_business | 2021,2022,2023 | Y | 0 | 20 | N | not_tested | blocked_publication_or_coverage |
| sido_industry_employee_size | 2021,2022,2023 | Y | 0 | 20 | N | not_tested | blocked_publication_or_coverage |

## 8. 공표일 및 First Eligible Period

- `target year + 2` 가정은 공식 공표일로 확정하지 않았다.
- 공식 release date가 비어 있는 source는 `blocked_publication` 또는 `development_only`로 남겼다.

## 9. 공장 Aggregate Source

- `kicox_factory_registration_stats.xlsx`에서 시군구 등록공장 현황을 파싱했다.
- 다만 기준연도와 historical publication date가 확인되지 않아 2021~2023 ML feature로 사용할 수 없다.

## 10. 공장 Micro Snapshot 탐색

- 현재 로컬 micro snapshot은 2020 계열 또는 target window 밖 자료로 판정했다.
- 2021, 2022, 2023 전국 snapshot은 계속 사용자 개입 요청 대상으로 남긴다.

## 11. KSIC Legacy Mapping

- 9→10과 10→11 공식 관계는 유지했다.
- 8→9 공식 관계가 없어 영향도 상위 미해결 code를 임의 유사명칭으로 해결하지 않았다.

## 12. 산업단지 Workbook Deep Extraction

- 대형 FactoryOn workbook 전체 sheet를 순회했다. Target-window period classification rows: `76`.
- 2021Q2 일부 stock 외에는 2021Q1~2023Q4의 연속 activity를 확보하지 못했다.

## 13. 산업동향 API Operation

- API를 반복 호출하지 않고, 로컬 공식 workbook sheet를 operation 후보로 등록했다.
- Period inventory rows: `60`.

## 14. 산업단지 Historical Activity

- 산업동향 workbook은 2026Q1 구조 확인용이다.
- Phase 4에서 복원한 2021Q2 stock은 release date가 없어 historical ML-ready가 아니다.

## 15. 산업단지 관할지역 및 Allocation

- 2025Q4 산업단지 현황 workbook에서 공식 시도·시군 행을 파싱했다.
- 다중 관할 단지는 별도 queue로 분리했다.
- 대표점 기반 전량배정은 계속 금지했다.

## 16. 한국형 Spatial Validation

- Archetype registry rows: `228`.
- Queen graph와 nearest-5 graph를 미래 후보로 동결하고, Rook/50km/100km는 diagnostic으로 유지했다.
- Actual residual이나 모델 성능은 archetype/fold 생성에 사용하지 않았다.

## 17. Source Triangulation

- 사업체·고용, 공장 aggregate·micro, 산업단지 workbook·API 비교축을 만들었으나 ML-ready source가 없어 정량 삼각검증은 보류했다.

## 18. Schema 및 Quality Audit

- 음수 count 자동 제거, 비공개값 0 변환, period jump 자동 제거는 하지 않았다.
- Schema drift는 source별 상태값으로 남겼다.

## 19. 사용자 개입 요청

| request_id | priority | source | blocked_gate | official_url | required_action | required_file | target_path | status | evidence | opened_at | resolved_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4B-001 | 1 | 전국사업체조사/KOSIS | business_employment_full_industry_release_date | https://kosis.kr | 시군구×산업대분류 사업체수·종사자수 2021, 2022, 2023 원표와 공식 공표일 또는 보도자료 경로 확인 | 2021-2023 sigungu x KSIC section establishment/employee source tables | data/raw/kosis/ | open | local mart has sido full-industry and sigungu manufacturing/mining, but not sigungu full-industry with release dates | 2026-07-18T01:42:46+09:00 |  |
| P4B-002 | 2 | KSIC 8->9 official crosswalk | ksic_legacy_mapping | https://kssc.mods.go.kr | 공식 KSIC 8차-9차 연계표 원본 확보 | KSIC 8->9 official relationship table | data/raw/ksic/ | open | Phase 4 has 9->10 and 10->11, but 8->9 remains missing | 2026-07-18T01:42:46+09:00 |  |
| P4B-003 | 3 | 국토교통부 산업단지 SHP | industrial_allocation_polygon | https://www.data.go.kr/data/3069832/fileData.do ; https://www.data.go.kr/data/3069833/fileData.do ; https://www.data.go.kr/data/3069836/fileData.do | 경계도면, 시설용지도면, 유치업종도면 중 최소 하나의 공식 SHP 원본 다운로드 | 산업단지 경계/시설용지/유치업종 SHP archive | data/raw/structural_phase3/manual/industrial_complex_polygon/ | open | local industrial_complex_polygon.zip is HTML, supplied DAM_PDAN is Point | 2026-07-18T01:42:46+09:00 |  |
| P4B-004 | 4 | FactoryOn 전국 등록공장 snapshot | factory_micro_history | https://www.factoryon.go.kr | 2021, 2022, 2023 전국 등록공장 원본 snapshot 또는 공식 archive 확보 | factory micro snapshot files for 2021-2023 | data/raw/structural_phase2/factoryon/manual/ | open | local factory micro files are outside target window | 2026-07-18T01:42:46+09:00 |  |

## 20. Source Gate Matrix

| source_group | status | gate_detail |
| --- | --- | --- |
| business_activity | blocked_user_action | blocked_publication_or_coverage |
| employment_activity | blocked_user_action | blocked_publication_or_coverage |
| factory_aggregate | blocked_publication | blocked_publication |
| factory_micro | blocked_missing_history | blocked_missing_history |
| industrial_activity | blocked_source_completion | blocked_source_completion |
| spatial_static | pass_static_context | pass |
| ksic_fine | blocked_mapping_quality | {"status": "blocked_mapping_quality", "row_mapping_rate": 0.9927106716775544, "employee_weighted_mapping_rate": 0.9872105617524882, "unresolved_top_impact_count": 50, "one_to_many_arbitrary_collapse": 0} |
| ksic_group | blocked_mapping_quality | {"status": "blocked_mapping_quality", "row_mapping_rate": 0.9934370822508639, "employee_weighted_mapping_rate": 0.9930024698266788, "unresolved_top_impact_count": 20, "one_to_many_arbitrary_collapse": 0} |
| ksic_division | blocked_mapping_quality | {"status": "blocked_mapping_quality", "row_mapping_rate": 0.9936640855550231, "employee_weighted_mapping_rate": 0.9933930196968209, "unresolved_top_impact_count": 115, "one_to_many_arbitrary_collapse": 0} |

## 21. Source 상태

- `spatial_static`: `pass_static_context`
- `business_activity`, `employment_activity`: `blocked_user_action`
- `factory_aggregate`: `blocked_publication`
- `factory_micro`: `blocked_missing_history`
- `industrial_activity`: `blocked_source_completion`
- `ksic_*`: `blocked_mapping_quality`

## 22. Bundle Eligibility

- `A0` baseline과 `A6/C6`의 geography-only future preregistration 후보만 구조적으로 가능하다.
- Business/Employment/Factory/Industrial bundle은 source hard gate 통과 전까지 학습 후보가 아니다.

## 23. Phase 5 진입조건

- `at_least_one_structural_source_ml_ready = false` 이므로 Phase 5 문서는 작성하지 않았다.

## 24. ML Restart 결정

- 결정: **blocked_source_completion**.
- New ML training: `prohibited_not_run`.

## 25. Blocking Issues

- 시군구×전산업 사업체·종사자 2021~2023 원표와 공식 공표일 부재.
- KSIC 8→9 공식 연계표 부재.
- 산업단지 공식 Polygon 또는 근무지/입주기업 주소 기반 allocation 근거 부재.
- 공장 2021~2023 micro snapshot 부재.
- 산업단지 activity의 target-window API 수집 및 총량 대조 미완료.

## 26. 다음 실행 항목

1. KOSIS 또는 원표에서 시군구×전산업 사업체·종사자 2021~2023과 공식 공표일을 확보한다.
2. 공식 산업단지 SHP를 확보해 다중관할 weight 또는 polygon intersection을 계산한다.
3. FactoryOn 2021~2023 snapshot 또는 공장 aggregate의 기준연도·공표일을 확보한다.
4. 최소 하나의 source가 gate를 통과한 뒤 Phase 5 사전등록 문서를 작성한다.
