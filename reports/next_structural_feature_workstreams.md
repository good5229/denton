# 다음 Structural Feature Workstreams

## 1. 실행 요약

전력 단독 residual correction은 종료됐고, 공식 운영 정책은 `global`로 유지한다. 다음 단계는 전력 feature를 독립 보정기가 아니라 공장등록, 산업단지, 건축활동, 사업체·고용 activity와 결합하는 구조 feature 실험으로 전환하는 것이다.

## 2. 전력 단독 정책 종료 상태

- experiment_status: `closed_no_confirmatory_challenger`
- champion: `global`
- challenger: `null`
- electricity_ml_correction: `inactive`
- same_actual_retuning_allowed: `false`

## 3. 전력 Pipeline 운영 현황

전력 pipeline은 계속 유지한다. 다만 신규 전력 데이터 갱신은 ML correction 재시작 조건이 아니다. 월별 source manifest, file hash, publication date, source vintage, schema drift, revision, negative value, duplicate key, publication lag drift를 점검한다.

## 4. 공장등록 Source 조사

| source | status | blocking issue | next action |
| --- | --- | --- | --- |
| FactoryOn 공장(기업)검색 | access_investigation | bulk download/API endpoint not verified | requires_registration_and_closure_dates |
| 공장등록 현황 통계정보 | schema_probe_downloaded_empty_workbook | prior workbook probe found title rows only | not_available_until_real_rows_found |
| 지자체별 공장등록 현황 | not_started | national coverage and schema consistency unknown | depends_on_snapshot_frequency_and_dates |

## 5. 산업단지 Activity 조사

| source | status | allocation need | blocking issue |
| --- | --- | --- | --- |
| 국가산업단지 산업동향정보 | candidate_not_collected | high | complex-to-sigungu allocation and publication lag not audited |
| 전국산업단지 통계/분기별 산업단지 동향 | not_started | high | file catalog and historical archive not enumerated |

## 6. 건축 인허가 Source 조사

| source | status | target sectors | blocking issue |
| --- | --- | --- | --- |
| 국토교통부 건축인허가 기본개요 | metadata_collected_source_file_pending | F00,L00 | bulk file/API route not confirmed in current repository |
| 건축데이터 민간개방시스템/건축HUB | not_started | F00,L00 | endpoint/authentication/sample download not verified |

## 7. 사업체·고용 Source 조사

사업체·고용 activity는 아직 source choice가 고정되지 않았다. 고용보험 사업장/피보험자, 사업자등록 개폐업, 지방행정 인허가, 전국사업체조사, 워크넷 구인공고를 비교하되, 산업분류와 publication lag가 확인되기 전까지 ML-ready로 판정하지 않는다.

## 8. Source별 Coverage 및 Publication Lag

| source_id | access | regional coverage | publication lag | ml ready | blocking issue |
| --- | --- | --- | --- | --- | --- |
| factoryon_factory_registration | access_investigation | unknown | unknown_requires_audit | not_ready | bulk endpoint and historical registration/closure dates not verified |
| kicox_factory_registration_stats | downloadable_but_empty_probe | not_verified | unknown_requires_audit | not_ready | downloaded workbook contains title rows only in prior probe |
| kicox_industrial_complex_trends | candidate | requires_complex_to_sigungu_allocation | unknown_requires_audit | not_ready | complex code standardization and multi-sigungu allocation rule not built |
| molit_building_permit_basic | metadata_collected_source_file_pending | expected_sigungu_if_bulk_available | unknown_requires_audit | not_ready | bulk/API access route and event date quality not verified |
| business_employment_activity | not_started | unknown | unknown_requires_audit | not_ready | source choice not fixed |
| card_sales_foot_traffic | not_started | pilot_first | unknown_requires_audit | not_ready | national free source not fixed |
| kepco_electricity_pipeline | active | sigungu_panel_available | implemented_for_current_vintage_selector | retained_for_combined_model_only | electricity-only correction closed; must not trigger ML restart by itself |

## 9. Feature 설계

| group | feature | sector | role | status |
| --- | --- | --- | --- | --- |
| factory_registration | active_factory_count | C00 | stock | planned |
| factory_registration | new_factory_registration_count | C00 | flow | planned |
| factory_registration | factory_closure_count | C00 | flow | planned |
| factory_registration | factory_employee_count | C00 | stock | planned |
| factory_registration | factory_site_area | C00 | stock | planned |
| industrial_complex_activity | industrial_complex_production | C00 | activity | planned |
| industrial_complex_activity | industrial_complex_exports | C00 | activity | planned |
| industrial_complex_activity | industrial_complex_employment | C00 | activity | planned |
| industrial_complex_activity | industrial_complex_utilization | C00 | activity | planned |
| building_activity | permit_floor_area | F00,L00 | pipeline | planned |
| building_activity | start_floor_area | F00,L00 | pipeline | planned |
| building_activity | approval_floor_area | F00,L00 | pipeline | planned |
| business_employment_activity | active_business_count | all,C00,G00,I00,F00 | activity | planned |
| business_employment_activity | insured_employee_count | all,C00,G00,I00,F00 | activity | planned |
| electricity_pipeline | industrial_kwh_per_factory | C00 | interaction | available_for_interaction_only |
| electricity_pipeline | industrial_kwh_per_employee | C00 | interaction | available_for_interaction_only |

## 10. ML-ready Gate

- C00: factory registration 또는 industrial complex activity가 ML-ready이고 coverage >= 90%, first eligible period, source vintage, common actual period, quality audit를 통과해야 한다.
- F00/L00: permit/start/approval event date validity와 use-code mapping이 완료돼야 한다.
- all: electricity 외 business/employment/building/card/foot-traffic source 중 하나 이상이 ML-ready여야 한다.

## 11. 차기 결합 실험 후보

C00에서는 `global + factory`, `global + industrial complex`, `global + factory + industrial complex`, `global + factory + electricity intensity`, `global + factory + industrial complex + electricity intensity`를 비교한다. 전력의 추가효과는 구조 feature가 있는 bundle과 전력 intensity를 추가한 bundle 차이로만 평가한다.

## 12. 미사용 Actual 관리

현재 confirmatory challenger가 없으므로 2024 이후 actual로 R2/R3b를 자동 평가하지 않는다. 새 structural policy가 actual 공개 전에 동결되면 confirmatory로 쓰고, 그렇지 않으면 development_extension으로 지정해 confirmatory 자격을 포기한다.

## 13. Blocking Issues

- FactoryOn bulk/API endpoint 미확인
- 공장등록 workbook 빈 데이터 문제
- 산업단지 complex-to-sigungu allocation 미구현
- BuildingHub bulk/API 접근 경로 미확정
- 사업체·고용 source choice 미고정

## 14. 다음 실행 항목

1. FactoryOn XLSX 내부구조 및 network 요청 조사
2. 산업단지 통계 source inventory와 complex allocation rule 작성
3. BuildingHub bulk/API 샘플 접근 확인
4. Source별 publication lag와 first eligible period 설계
5. ML-ready source가 생기기 전까지 모델 학습 금지

## 15. 최종 재개 판단

현 시점에서는 시군구 ML correction 재개 조건이 충족되지 않았다. 다음 실험은 전력 단독이 아니라 structural source가 ML-ready가 된 뒤 사전등록 프로토콜을 commit하고 진행한다.
