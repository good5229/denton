# 다음 Structural Feature Workstreams

## 1. 실행 요약

공공데이터포털 키(`DATA_GO_KR_DECODING`/`DATA_GO_KR_ENCODING`)를 사용해 구조 feature 후보를 다시 점검했다. 사용자가 지적한 대로 `not_probed`였던 다수 항목은 API가 아니라 웹페이지의 CSV/XLSX 다운로드형 파일데이터로 재분류했다. 전력 단독 correction은 계속 종료 상태이며, 이번 작업은 새 모델 학습이 아니라 실제 파일 확보, API 승인 확인, publication lag/vintage 가능성, ML-ready gate 판정에 한정한다.

- API traffic policy: 승인 확인용 endpoint별 `1`행 샘플만 호출, 총 probe endpoint `4`개.
- 파일데이터 다운로드는 API 일일 트래픽을 소비하지 않는 `contentUrl` 직접 다운로드 경로를 우선 사용한다.
- 사용자가 건축HUB 활용승인 완료를 확인했으며, 서울 열린데이터광장 키(`SEOUL_OPENAPI_KEY`)도 `.env`에 추가했다.
- LOCALDATA는 API 페이지 접근 자체가 되지 않는 상태로 보고되어 현재 workstream에서는 보류한다.
- 건축HUB 전용 readiness probe를 추가해 schema, request manifest, 날짜 품질, 용도/지역 sample crosswalk, feature pilot 산출물을 생성했다. 새 ML 학습은 실행하지 않았다.

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
| 한국산업단지공단_전국등록공장현황_등록공장현황자료 | sample_downloaded | 200 | 20241231 |  |
| 한국산업단지공단_전국등록공장현황 | sample_downloaded | 200 | 20200229 |  |
| 한국산업단지공단_공장등록생산정보조회서비스 | blocked | 0 | not_verified | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" |

## 5. 산업단지 조사 결과

| source | access | rows | blocking issue |
| --- | --- | ---: | --- |
| 한국산업단지공단_국가산업단지 산업동향정보 | sample_downloaded | 200 |  |
| 한국산업단지공단_산업동향조사 통계 조회 서비스 - 단지별 생산실적 | blocked | 0 | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" |

## 6. 건축자료 조사 결과

| source | access | rows | blocking issue |
| --- | --- | ---: | --- |
| 국토교통부_건축인허가 기본개요 | external_link_confirmed | 0 | external link; direct file download is outside data.go.kr contentUrl |
| 국토교통부_건축HUB_건축인허가 기본개요 | sample_downloaded | 5 unique sample rows | schema 42 fields; historical/query probe logged; full inventory and gates not completed |

### 6.1 건축HUB Readiness Probe

| item | result |
| --- | --- |
| request headers | `User-Agent: Mozilla/5.0`, `Accept: application/json, application/xml, text/xml, */*` required |
| successful sample query | `sigunguCd=11680`, `bjdongCd=10300`, `numOfRows=1` |
| schema fields | 42 |
| unique sample rows | 5 |
| request manifest rows | 9 |
| `bjdongCd` omitted | body exists but no usable rows; not accepted as sigungu-wide collection route |
| `bjdongCd` empty | normal response, `totalCount=0` |
| representative legal-dong probes | Jongno and Busan Haeundae returned rows |
| historical month probes | 2021-01 and 2022-01 returned 0 for Gangnam/gaepo; 2023-01 and 2023-12 returned rows |
| start-date field mapping | actual response uses `realStcnsDay`, not `stcnsDay` |
| publication lag | still unknown; retrieval snapshot preserved but first eligible period not implemented |

Generated artifacts:

- `data/processed/buildinghub_response_schema.json`
- `data/processed/buildinghub_sample_row.csv`
- `data/processed/buildinghub_schema_fingerprint.csv`
- `data/processed/buildinghub_request_manifest.csv`
- `data/processed/buildinghub_date_quality_audit.csv`
- `data/processed/buildinghub_event_sequence_audit.csv`
- `data/processed/buildinghub_main_purpose_crosswalk.csv`
- `data/processed/buildinghub_region_crosswalk.csv`
- `data/processed/buildinghub_feature_table_pilot.csv`
- `data/processed/buildinghub_ml_ready_gate_status.csv`

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
| data_go_kr_factory_registration_snapshot_file | sample_downloaded | parser_development | blocked | Complete schema mapping, full historical inventory, region crosswalk, publication lag audit, and quality gates |
| data_go_kr_factory_full_snapshot_20200229_file | sample_downloaded | parser_development | blocked | Complete schema mapping, full historical inventory, region crosswalk, publication lag audit, and quality gates |
| data_go_kr_industrial_complex_trends_file | sample_downloaded | parser_development | blocked | Complete schema mapping, full historical inventory, region crosswalk, publication lag audit, and quality gates |
| data_go_kr_molit_building_permit_basic_link | external_link_confirmed | blocked | blocked | Complete schema mapping, full historical inventory, region crosswalk, publication lag audit, and quality gates |
| data_go_kr_factory_realtime_api | blocked | blocked | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_industrial_complex_prd_api | blocked | blocked | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_buildinghub_ap_basis | sample_downloaded | parser_development | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| data_go_kr_small_shop_large_upjong_api | sample_downloaded | parser_development | blocked | Complete historical inventory, regional coverage, publication lag, and quality gates before ML use |
| seoul_open_data | credential_available | not_started | pilot_only | 후보 endpoint inventory 및 1행 probe |
| localdata_business_license_delta_api | blocked | blocked | blocked | 공공데이터포털 키가 아니라 LOCALDATA 개발용/운영용 API 신청이 필요하며 API는 변동분 중심이다. |

## 9. Coverage

- 공장등록 snapshot feature rows: `32`
- 파일데이터는 주소 기반 시군구 추출이 가능하면 development feature 후보로만 둔다. 아직 official actual 모집단과 crosswalk 검증을 끝내지 않았으므로 ML-ready는 아니다.
- 산업단지 파일/API는 단지-시군구 배분 규칙이 없으므로 대표주소 전량 배정은 금지한다.

## 10. Publication Lag

- 공장등록 snapshot 파일은 공개 페이지의 등록일을 보수적 publication date로 사용할 수 있다.
- 건축HUB는 월간 갱신으로 공표되지만 prediction-origin별 `first_eligible_period`는 샘플 확보 후 실제 응답/갱신일 기준으로 다시 고정한다.
- 건축HUB retrieval snapshot은 `data/raw/buildinghub/vintage_YYYYMMDD/`에 저장했다. 다만 historical publication lag는 아직 검증되지 않았으므로 과거 observation의 최초 공개일로 소급 사용하지 않는다.
- API source는 승인 확인용 1행 probe만 수행했으므로 publication lag 측정에는 아직 쓰지 않는다.

## 11. Region Crosswalk

- 공장등록 주소 기반 `sido/sigungu` 1차 parser는 스크립트에 구현했다.
- 건축HUB sample crosswalk는 `platPlc` 문자열을 파싱한 임시 mapping이다. 전체 수집 전 공식 법정동 코드표를 확보해 `sigunguCd`, `bjdongCd` 기반 crosswalk로 교체해야 한다.
- 최종 ML-ready에는 official actual 시군구 모집단 기준 `unmatched_regions = 0`이 필요하다.
- 세종, 통합시, 행정구가 있는 시 지역은 별도 crosswalk rule을 보존해야 한다.

## 12. Feature Table

- `factory_feature_table.csv`: annual snapshot 기반 `active_factory_count_snapshot`, `industrial_complex_factory_share_snapshot` 생성.
- `buildinghub_feature_table_pilot.csv`: 샘플 row에서 유효한 허가/착공/사용승인 날짜가 있는 경우에만 pilot feature를 생성한다. `first_eligible_period`는 publication lag audit 전까지 비워 둔다.
- `sigungu_feature_key`, `observation_period`, `prediction_origin`, `feature_name`, `feature_value`, `first_eligible_period`, `source_version` 형식을 사용한다.
- 등록일·폐쇄일이 없으면 flow feature와 월/분기 stock 복원은 만들지 않는다.

## 13. Quality Audit

| source_id | quality status | issue |
| --- | --- | --- |
| data_go_kr_factory_registration_snapshot_file | quality_validation |  |
| data_go_kr_factory_full_snapshot_20200229_file | quality_validation |  |
| data_go_kr_industrial_complex_trends_file | quality_validation |  |
| data_go_kr_molit_building_permit_basic_link | blocked | external link; direct file download is outside data.go.kr contentUrl |
| data_go_kr_factory_realtime_api | blocked | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" |
| data_go_kr_industrial_complex_prd_api | blocked | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" |
| data_go_kr_buildinghub_ap_basis | quality_validation | schema/date/query probe complete for sample; full historical inventory, official crosswalk, publication lag not completed |
| data_go_kr_small_shop_large_upjong_api | not_started | sample rows downloaded only; full historical inventory and gates not completed |
| localdata_business_license_delta_api | blocked | user_reported_api_page_unavailable_2026-07-17 |

## 14. ML-ready Gate

| source_id | access | historical | vintage | feature table | ml-ready |
| --- | --- | --- | --- | --- | --- |
| data_go_kr_factory_registration_snapshot_file | pass | 20241231 | Y | partial | blocked |
| data_go_kr_factory_full_snapshot_20200229_file | pass | 20200229 | Y | partial | blocked |
| data_go_kr_industrial_complex_trends_file | pass | latest_quarter_file | Y | partial | blocked |
| data_go_kr_molit_building_permit_basic_link | fail | hub_bulk_download | Y | no | blocked |
| data_go_kr_factory_realtime_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_industrial_complex_prd_api | fail | not_verified | not_verified | no | blocked |
| data_go_kr_buildinghub_ap_basis | pass | probe_only | partial_snapshot | partial | blocked |
| data_go_kr_small_shop_large_upjong_api | pass | not_verified | not_verified | partial | blocked |
| localdata_business_license_delta_api | fail | not_verified | not_verified | no | blocked |

## 15. Blocking Issues

- 파일데이터형 source는 활용신청 대상이 아니라 다운로드/스키마/파서/교차표 검증 대상이다.
- `unauthorized` API와 소상공인시장진흥공단 상가정보 API는 사용자가 활용신청을 완료했으므로, 승인 반영 여부는 1행 probe 결과로만 판단한다.
- API 일일 트래픽 보호를 위해 대량 수집은 별도 rate limit, 캐시, resume manifest 기준으로만 실행한다. 건축HUB probe script는 `request_interval_seconds >= 0.5`, cache, manifest를 구현했다.
- LOCALDATA 인허가 API는 페이지 접근 불가 상태이므로 API 페이지 복구, 기존 승인정보 확인, 공식 대용량 다운로드 경로 확보, 공식 문의 답변 중 하나가 발생할 때까지 보류한다.

## 16. 다음 실험 재개 판단

아직 `at_least_one_structural_source_ml_ready = false`다. 따라서 C00/F00/L00/all 어느 쪽도 모델 학습을 재개하지 않는다. 파일데이터 source는 실제 row 또는 샘플이 확보돼도 crosswalk, vintage, quality gate가 끝나기 전까지 development feature 후보에만 둔다.

## 17. 미사용 Actual 관리

frozen structural challenger가 없으므로 2024 이후 official actual을 confirmatory로 투입하지 않는다. 새 structural policy가 actual 공개 전에 동결될 때만 confirmatory role을 부여한다.

## 18. 다음 실행 항목

1. 건축HUB 법정동 코드표를 확보하고 `sigunguCd`/`bjdongCd` 기반 request universe를 만든다.
2. 건축HUB 2021~2023 historical inventory를 월별 `totalCount` 중심으로 확장하되, row 대량 수집 전 request budget과 resume policy를 고정한다.
3. 건축HUB 주용도 crosswalk를 sample rule에서 공식/전체 observed code 기반으로 확장한다.
4. 서울 열린데이터광장 후보 endpoint를 1행 probe하고 건축HUB 강남구 건축 이벤트와 교차검증할 후보를 고른다.
5. 공장등록 파일데이터와 산업단지 파일데이터의 schema mapping, 공식 region crosswalk, allocation rule을 이어서 작성한다.

### 활용신청/다운로드 경로 재분류

| source | where | route | observed issue | needs user application |
| --- | --- | --- | --- | --- |
| 한국산업단지공단_전국등록공장현황_등록공장현황자료 | https://www.data.go.kr/data/15105482/fileData.do | 공공데이터포털 파일데이터 API 활용신청 또는 원문파일 다운로드 |  | N_file_or_external_download_route |
| 한국산업단지공단_전국등록공장현황 | https://www.data.go.kr/data/15106170/fileData.do | 공공데이터포털 파일데이터 API 활용신청 또는 원문파일 다운로드 |  | N_file_or_external_download_route |
| 한국산업단지공단_공장등록생산정보조회서비스 | https://www.data.go.kr/data/15087611/openapi.do | 공공데이터포털 활용신청 | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" | N_api_reachable_parameter_required |
| 한국산업단지공단_산업동향조사 통계 조회 서비스 | https://www.data.go.kr/data/15152884/openapi.do | 공공데이터포털 활용신청 | "<response><header><resultCode>11</resultCode><resultMsg>NO_MANDATORY_REQUEST_PARAMETERS_ERROR</resultMsg></header></response>" | N_api_reachable_parameter_required |
| 한국산업단지공단_국가산업단지 산업동향정보 | https://www.data.go.kr/data/3042071/fileData.do | 공공데이터포털 원문파일 다운로드 확인 |  | N_file_or_external_download_route |
| 국토교통부_건축HUB_건축인허가정보 서비스 | https://www.data.go.kr/data/15136267/openapi.do | 공공데이터포털 활용신청 | sample rows downloaded only; full historical inventory and gates not completed | N_api_sample_reachable |
| 국토교통부_건축인허가 기본개요 | https://www.data.go.kr/data/15044695/fileData.do?recommendDataYn=Y | 건축HUB 대용량/공공데이터포털 경로 확인 | external link; direct file download is outside data.go.kr contentUrl | N_file_or_external_download_route |
| 지방행정인허가데이터개방 Open API | https://www.localdata.go.kr/devcenter/applyGroupApi.do?menuNo=20002 | LOCALDATA 별도 API 신청 | user_reported_api_page_unavailable_2026-07-17 | Y_or_confirm_existing_approval |
| 소상공인시장진흥공단_상가(상권)정보 | https://www.data.go.kr/data/15012005/openapi.do | 공공데이터포털 활용신청 | sample rows downloaded only; full historical inventory and gates not completed | N_api_sample_reachable |
