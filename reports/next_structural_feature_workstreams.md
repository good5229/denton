# 다음 Structural Feature Workstreams

## 1. 실행 요약

공공데이터포털 키(`DATA_GO_KR_DECODING`/`DATA_GO_KR_ENCODING`)를 사용해 구조 feature 후보를 다시 점검했다. 전력 단독 correction은 계속 종료 상태이며, 이번 작업은 새 모델 학습이 아니라 실제 row 확보, 활용신청 필요 여부, publication lag/vintage 가능성, ML-ready gate 판정에 한정한다.

## 2. 현재 ML 상태

- municipality_ml_status: `blocked_waiting_for_structural_source`
- operating_policy: `global`
- electricity_only_policy: `closed`
- new_ml_training: `prohibited`

## 3. 전력 Pipeline 상태

KEPCO 전력 pipeline은 유지하되 독립 residual correction으로 재개하지 않는다. 전력은 공장등록·산업단지·건축·사업체 source가 ML-ready가 된 뒤 interaction 또는 보조 feature로만 비교한다.

## 4. 공장등록 조사 결과

| source | access | rows | coverage | blocking issue |
| --- | --- | ---: | --- | --- |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료_20200131 | blocked | 0 | 2020,2022,2023,2024 snapshots; 2021 missing | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료_20200229 | blocked | 0 | 2020,2022,2023,2024 snapshots; 2021 missing | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료_20221231 | blocked | 0 | 2020,2022,2023,2024 snapshots; 2021 missing | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료_20231231 | blocked | 0 | 2020,2022,2023,2024 snapshots; 2021 missing | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료_20241231 | blocked | 0 | 2020,2022,2023,2024 snapshots; 2021 missing | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_공장등록생산정보조회서비스 | blocked | 0 | not_verified | Unauthorized |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료 | blocked | 0 | not_verified | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황 | blocked | 0 | not_verified | not_probed |

## 5. 산업단지 조사 결과

| source | access | rows | blocking issue |
| --- | --- | ---: | --- |
| 한국산업단지공단_산업동향조사 통계 조회 서비스 - 단지별 생산실적 | blocked | 0 | Unauthorized |
| 한국산업단지공단_산업동향조사 통계 조회 서비스 | blocked | 0 | Unauthorized |
| 한국산업단지공단_국가산업단지 산업동향정보 | blocked | 0 | not_probed |

## 6. 건축자료 조사 결과

| source | access | rows | blocking issue |
| --- | --- | ---: | --- |
| 국토교통부_건축HUB_건축인허가 기본개요 | blocked | 0 | Unauthorized |
| 국토교통부_건축인허가 기본개요 | blocked | 0 | not_probed |

## 7. 사업체·고용 Source 평가

| rank | source | score | note |
| ---: | --- | ---: | --- |
| 1 | 전국사업체조사/KOSIS | 80/100 | stock feature로 안정적이나 nowcasting activity source로는 시차가 길다 |
| 2 | 지방행정인허가데이터개방 | 75/100 | 영업상태/허가일/폐업 등 activity성이 좋지만 API는 변동분 중심이고 별도 신청 필요 |
| 3 | 소상공인시장진흥공단 상가(상권)정보 | 74/100 | 상가 stock proxy로 유용하나 activity flow와 publication lag 확인 필요 |
| 4 | 고용보험 사업장·피보험자 | 60/100 | 시군구×산업 공개 집계의 지속 접근성과 무료 API 여부 재확인 필요 |

## 8. Source Inventory

| source_id | access | parser | ml_ready | next_action |
| --- | --- | --- | --- | --- |
| factory_snapshot_odcloud | blocked | blocked | blocked | Use as annual stock proxy; inspect richer realtime API or local files for dates/industry/area/employee fields |
| factory_snapshot_odcloud | blocked | blocked | blocked | Use as annual stock proxy; inspect richer realtime API or local files for dates/industry/area/employee fields |
| factory_snapshot_odcloud | blocked | blocked | blocked | Use as annual stock proxy; inspect richer realtime API or local files for dates/industry/area/employee fields |
| factory_snapshot_odcloud | blocked | blocked | blocked | Use as annual stock proxy; inspect richer realtime API or local files for dates/industry/area/employee fields |
| factory_snapshot_odcloud | blocked | blocked | blocked | Use as annual stock proxy; inspect richer realtime API or local files for dates/industry/area/employee fields |
| data_go_kr_factory_realtime_api | blocked | blocked | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_industrial_complex_prd_api | blocked | blocked | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_buildinghub_ap_basis | blocked | blocked | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_factory_snapshot_odcloud | blocked | blocked | blocked | 2020, 2022, 2023, 2024 snapshot UDDI가 존재하나 현재 키로는 odcloud API가 등록되지 않은 인증키로 응답했다. |
| data_go_kr_factory_full_snapshot_20200229 | blocked | blocked | blocked | 2020년 2월 snapshot이며 회사명, 종업원 수, 관할 산단, 업종, 생산품, 면적, 주소가 포함된 richer source 후보. |
| data_go_kr_industrial_complex_stats_api | blocked | blocked | blocked | 개발단계 자동승인, 운영단계 심의승인. Base URL: apis.data.go.kr/B550624/indparkstats |
| data_go_kr_industrial_complex_trends_file | blocked | blocked | blocked | 분기별 국가산업단지 산업동향 XLSX/CSV 파일. API 승인과 별도로 원문파일 다운로드가 가능한지 확인 필요. |
| data_go_kr_arch_pms_hub_api | blocked | blocked | blocked | 개발단계 자동승인, 운영단계 자동승인. Base URL: apis.data.go.kr/1613000/ArchPmsHubService |
| data_go_kr_molit_building_permit_basic_file | blocked | blocked | blocked | 이전 probe에서는 메타데이터만 확보했고 원천은 건축HUB 대용량 제공 구조로 확인됐다. |
| localdata_business_license_delta_api | blocked | blocked | blocked | 공공데이터포털 키가 아니라 LOCALDATA 개발용/운영용 API 신청이 필요하며 API는 변동분 중심이다. |
| data_go_kr_small_shop_api | blocked | blocked | blocked | 상가업소 stock proxy로 유용하지만 매출이나 고용이 아니므로 source score에서 activity성은 낮게 둔다. |

## 9. Coverage

- 공장등록 snapshot feature rows: `0`
- 전국등록공장현황 snapshot은 명세상 주소 기반 시군구 추출이 가능하지만, 현재 키로 실제 row를 받지 못해 coverage 계산은 보류한다.
- 산업단지 API는 단지-시군구 배분 규칙이 없으므로 대표주소 전량 배정은 금지한다.

## 10. Publication Lag

- 공장등록 snapshot 파일은 공개 페이지의 등록일을 보수적 publication date로 사용할 수 있다.
- 건축HUB는 월간 갱신으로 공표되지만 prediction-origin별 `first_eligible_period`는 샘플 확보 후 실제 응답/갱신일 기준으로 다시 고정한다.
- 활용신청 미승인 또는 샘플 미확보 source는 publication lag를 측정하지 않는다.

## 11. Region Crosswalk

- 공장등록 주소 기반 `sido/sigungu` 1차 parser는 스크립트에 구현했다.
- 최종 ML-ready에는 official actual 시군구 모집단 기준 `unmatched_regions = 0`이 필요하다.
- 세종, 통합시, 행정구가 있는 시 지역은 별도 crosswalk rule을 보존해야 한다.

## 12. Feature Table

- `factory_feature_table.csv`: 파일 구조는 생성했지만 현재 키가 승인되지 않아 row는 비어 있다.
- `sigungu_feature_key`, `observation_period`, `prediction_origin`, `feature_name`, `feature_value`, `first_eligible_period`, `source_version` 형식을 사용한다.
- 등록일·폐쇄일이 없으면 flow feature와 월/분기 stock 복원은 만들지 않는다.

## 13. Quality Audit

| source_id | quality status | issue |
| --- | --- | --- |
| factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| data_go_kr_factory_realtime_api | blocked | Unauthorized |
| data_go_kr_industrial_complex_prd_api | blocked | Unauthorized |
| data_go_kr_buildinghub_ap_basis | blocked | Unauthorized |
| data_go_kr_factory_snapshot_odcloud | blocked | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| data_go_kr_factory_full_snapshot_20200229 | blocked | not_probed |
| data_go_kr_industrial_complex_stats_api | blocked | Unauthorized |
| data_go_kr_industrial_complex_trends_file | blocked | not_probed |
| data_go_kr_arch_pms_hub_api | blocked | Unauthorized |
| data_go_kr_molit_building_permit_basic_file | blocked | not_probed |
| localdata_business_license_delta_api | blocked | not_probed |
| data_go_kr_small_shop_api | blocked | not_probed |

## 14. ML-ready Gate

| source_id | access | historical | vintage | feature table | ml-ready |
| --- | --- | --- | --- | --- | --- |
| factory_snapshot_odcloud | fail | 2020,2022,2023,2024 snapshots; 2021 missing | Y | no | blocked |
| factory_snapshot_odcloud | fail | 2020,2022,2023,2024 snapshots; 2021 missing | Y | no | blocked |
| factory_snapshot_odcloud | fail | 2020,2022,2023,2024 snapshots; 2021 missing | Y | no | blocked |
| factory_snapshot_odcloud | fail | 2020,2022,2023,2024 snapshots; 2021 missing | Y | no | blocked |
| factory_snapshot_odcloud | fail | 2020,2022,2023,2024 snapshots; 2021 missing | Y | no | blocked |
| data_go_kr_factory_realtime_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_industrial_complex_prd_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_buildinghub_ap_basis | fail | not_verified | not_verified | no | blocked |
| data_go_kr_factory_snapshot_odcloud | fail | not_verified | not_verified | no | blocked |
| data_go_kr_factory_full_snapshot_20200229 | fail | not_verified | not_verified | no | blocked |
| data_go_kr_industrial_complex_stats_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_industrial_complex_trends_file | fail | not_verified | not_verified | no | blocked |
| data_go_kr_arch_pms_hub_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_molit_building_permit_basic_file | fail | not_verified | not_verified | no | blocked |
| localdata_business_license_delta_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_small_shop_api | fail | not_verified | not_verified | no | blocked |

## 15. Blocking Issues

- 현재 `.env` 키는 확인됐지만 대상 공공데이터포털 서비스에 등록되지 않았거나 활용신청 승인이 연결되지 않아 실제 row를 받지 못했다.
- 공장등록 realtime API와 산업동향조사 API는 활용신청 승인 여부를 실제 호출 결과로 확인해야 하며, 미승인 시 사용자가 공공데이터포털에서 신청해야 한다.
- 건축HUB는 자동승인 대상이지만 API 응답 샘플 확보 후 허가·착공·승인을 섞지 않는 parser가 필요하다.
- LOCALDATA 인허가 API는 공공데이터포털 키가 아니라 별도 신청이 필요하다.

## 16. 다음 실험 재개 판단

아직 `at_least_one_structural_source_ml_ready = false`다. 따라서 C00/F00/L00/all 어느 쪽도 모델 학습을 재개하지 않는다. 공장등록 snapshot은 아직 실제 row를 받지 못했으므로 development feature 후보로도 활성화하지 않는다.

## 17. 미사용 Actual 관리

frozen structural challenger가 없으므로 2024 이후 official actual을 confirmatory로 투입하지 않는다. 새 structural policy가 actual 공개 전에 동결될 때만 confirmatory role을 부여한다.

## 18. 다음 실행 항목

1. 아래 활용신청 필요 목록을 공공데이터포털/LOCALDATA에서 승인 상태로 만든다.
2. 승인된 API에 대해 2021~2023 공통기간 historical inventory를 만든다.
3. 공장등록 주소 parser를 official region crosswalk와 대조해 unmatched region을 0으로 만든다.
4. 산업단지 complex-to-sigungu allocation rule을 기업주소·면적·고용·GIS 순서로 작성한다.
5. 건축HUB 기본개요 샘플에서 허가일, 실제착공일, 사용승인일을 분리한 월간 집계를 만든다.

### 활용신청 필요 목록

| source | where | user action | current issue |
| --- | --- | --- | --- |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료 | https://www.data.go.kr/data/15105482/fileData.do | 공공데이터포털 파일데이터 API 활용신청 또는 원문파일 다운로드 | {"code":-4,"msg":"등록되지 않은 인증키 입니다."} |
| 한국산업단지공단_전국등록공장현황 | https://www.data.go.kr/data/15106170/fileData.do | 공공데이터포털 파일데이터 API 활용신청 또는 원문파일 다운로드 | not_probed |
| 한국산업단지공단_공장등록생산정보조회서비스 | https://www.data.go.kr/data/15087611/openapi.do | 공공데이터포털 활용신청 | Unauthorized |
| 한국산업단지공단_산업동향조사 통계 조회 서비스 | https://www.data.go.kr/data/15152884/openapi.do | 공공데이터포털 활용신청 | Unauthorized |
| 한국산업단지공단_국가산업단지 산업동향정보 | https://www.data.go.kr/data/3042071/fileData.do | 공공데이터포털 원문파일 다운로드 확인 | not_probed |
| 국토교통부_건축HUB_건축인허가정보 서비스 | https://www.data.go.kr/data/15136267/openapi.do | 공공데이터포털 활용신청 | Unauthorized |
| 국토교통부_건축인허가 기본개요 | https://www.data.go.kr/data/15044695/fileData.do?recommendDataYn=Y | 건축HUB 대용량/공공데이터포털 경로 확인 | not_probed |
| 지방행정인허가데이터개방 Open API | https://www.localdata.go.kr/devcenter/applyGroupApi.do?menuNo=20002 | LOCALDATA 별도 API 신청 | not_probed |
| 소상공인시장진흥공단_상가(상권)정보 | https://www.data.go.kr/data/15012005/openapi.do | 공공데이터포털 활용신청 | not_probed |
