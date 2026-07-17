# 다음 Structural Feature Workstreams

## 1. 실행 요약

공공데이터포털 키(`DATA_GO_KR_DECODING`/`DATA_GO_KR_ENCODING`)를 사용해 구조 feature 후보를 다시 점검했다. 사용자가 지적한 대로 `not_probed`였던 다수 항목은 API가 아니라 웹페이지의 CSV/XLSX 다운로드형 파일데이터로 재분류했다. 전력 단독 correction은 계속 종료 상태이며, 이번 작업은 새 모델 학습이 아니라 실제 파일 확보, API 승인 확인, publication lag/vintage 가능성, ML-ready gate 판정에 한정한다.

- API traffic policy: 승인 확인용 endpoint별 `1`행 샘플만 호출, 총 probe endpoint `4`개.
- 파일데이터 다운로드는 API 일일 트래픽을 소비하지 않는 `contentUrl` 직접 다운로드 경로를 우선 사용한다.
- 사용자가 건축HUB 활용승인 완료를 확인했으며, 서울 열린데이터광장 키(`SEOUL_OPENAPI_KEY`)도 `.env`에 추가했다.
- LOCALDATA는 API 페이지 접근 자체가 되지 않는 상태로 보고되어 현재 workstream에서는 보류한다.
- 건축HUB 전용 readiness probe를 추가해 schema, request manifest, 날짜 품질, 용도/지역 sample crosswalk, feature pilot 산출물을 생성했다. 새 ML 학습은 실행하지 않았다.
- 건축HUB Pre-ML readiness 실험에서 사용자가 제공한 공식 법정동코드 전체자료(`data/raw/buildinghub/법정동코드 전체자료.txt`, CP949)를 우선 사용하도록 전환했다. 법정동 request universe와 3개 시군구 파일럿 historical inventory는 생성됐지만, 전국 coverage·publication lag·first eligible period가 아직 없어 ML-ready는 아니다.

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
- `data/processed/buildinghub_legal_dong_request_universe.csv`
- `data/processed/buildinghub_historical_inventory.csv`
- `data/processed/buildinghub_monthly_total_count.csv`
- `data/processed/buildinghub_collection_budget.json`
- `data/processed/buildinghub_historical_schema_audit.csv`
- `data/processed/buildinghub_purpose_code_inventory.csv`
- `data/processed/buildinghub_official_region_crosswalk.csv`
- `data/processed/buildinghub_publication_lag_audit.csv`
- `data/processed/buildinghub_snapshot_revision_audit.csv`
- `data/processed/buildinghub_feature_table.csv`
- `data/processed/buildinghub_final_ml_readiness.json`

## 건축HUB Request Universe

| item | result |
| --- | --- |
| official source | 행정안전부_행정표준코드_법정동코드 |
| data.go.kr endpoint | `http://apis.data.go.kr/1741000/StanReginCd/getStanReginCdList` |
| API result | 기존 키 기준 HTTP 403이었으나 사용자가 활용신청 완료 |
| local official file | `data/raw/buildinghub/법정동코드 전체자료.txt`, CP949, tab-delimited |
| legal code raw rows | 53,387 |
| request universe rows | 52,850 |
| active/detail universe rows | 20,276 |
| official sigungu crosswalk rows | 256 |
| status | built_for_pilot |
| remaining issue | API 승인 반영 여부는 별도 재확인 필요. 현재는 로컬 공식 파일을 기준으로 request universe를 사용한다. |

Request universe는 건축HUB 전국 수집의 선행조건이다. `bjdongCd` 생략 또는 빈 값 조회를 전국 수집 방식으로 사용하지 않는다.

## 건축HUB Historical Inventory

| item | result |
| --- | --- |
| representative months | `202101`, `202106`, `202112`, `202201`, `202206`, `202212`, `202301`, `202306`, `202312` |
| pilot regions | 서울특별시 종로구, 서울특별시 강남구, 부산광역시 해운대구 |
| pilot legal-dong rows | 109 |
| pilot inventory requests | 981 |
| normal response rate | 100% |
| positive totalCount requests | 196 |
| pilot totalCount sum | 884 |
| positive regions | 서울특별시 종로구, 서울특별시 강남구, 부산광역시 해운대구 |
| full inventory decision | not started |

2021~2023 전체 row 수집은 진행하지 않았다. 현재 active/detail 법정동 20,276개와 36개월을 단순 곱하면 전국 월별 `totalCount` inventory만 최소 729,936회 요청이 필요하다. 따라서 전국 수집은 월·지역 chunk, 캐시, resume manifest, 일일 트래픽 상한을 고정한 뒤 별도 승인 단계로 진행한다.

## 건축 Event 날짜 품질

기존 sample probe 기준으로 허가일은 `archPmsDay`, 실제 착공일은 `realStcnsDay`, 사용승인일은 `useAprDay`로 분리한다. 이번 파일럿에서는 196개 반환 샘플 중 136개만 요청 월과 세 날짜 중 하나가 직접 일치했다. 샘플 관측 날짜 범위도 `20000601`~`20231229`로 넓게 나타나므로, 현재 `startDate`/`endDate` 조회 결과를 그대로 월별 feature로 확정해서는 안 된다.

다음 단계에서는 요청 파라미터가 어떤 이벤트 날짜를 필터링하는지 공식 문서와 추가 probe로 검증하고, `archPmsDay`, `realStcnsDay`, `useAprDay`별로 별도 endpoint/parameter 또는 사후 필터링 규칙을 고정해야 한다.

## 건축HUB Event Date Filter Semantics

Experiment D1을 실행했다. 기존 건축HUB historical pilot cache에서 196개 unique sample row를 읽고, 패턴별로 50개 target row를 선정했다. 선정 표본에는 `permit_date_only_available` 19개, `all_three_dates_available` 27개, `dates_in_different_months` 30개, `dates_in_different_years` 24개가 포함됐다.

각 target row의 이벤트 날짜를 `permit=archPmsDay`, `start=realStcnsDay`, `approval=useAprDay`로 분리한 뒤, 존재하는 이벤트 날짜 108개에 대해 다음 5개 window를 조회했다.

| window | definition |
| --- | --- |
| exact_day | event_date to event_date |
| month_window | event month first day to last day |
| previous_month | previous calendar month |
| next_month | next calendar month |
| plus_minus_1_day | event_date -1 to event_date +1 |

총 540개 probe request가 실행됐고, 모든 응답은 정상으로 처리됐다. 주요 결과는 다음과 같다.

| event_type | window | query | target_returned_rate | single_event_match_rate | unknown_rate | decision |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| permit | exact_day | 50 | 0.24 | 1.00 | 0.00 | fail |
| permit | month_window | 50 | 0.28 | 0.93 | 0.00 | fail |
| start | exact_day | 28 | 0.04 | 1.00 | 0.00 | fail |
| start | month_window | 28 | 0.04 | 0.00 | 0.00 | fail |
| approval | exact_day | 30 | 0.90 | 1.00 | 0.00 | fail |
| approval | month_window | 30 | 0.90 | 1.00 | 0.00 | fail |

통과 기준은 `single_event_match_rate >= 0.95`, `unknown_filter_match_rate <= 0.05`, 지역·연도 간 동일 규칙 확인이다. Approval은 가장 그럴듯하지만 target 반환율이 90%에 머물러 아직 기준을 충족하지 못했다. Permit과 Start는 target 반환율이 매우 낮아 `startDate/endDate`가 각각 허가일·착공일 필터라고 볼 수 없다.

따라서 현재 기본개요 endpoint의 `startDate/endDate`를 월별 Event 필터로 채택하지 않는다. 전국 row 수집과 production feature table 재생성은 계속 보류한다.

Generated artifacts:

- `data/processed/buildinghub_date_field_inventory.csv`
- `data/processed/buildinghub_date_filter_semantics_probe.csv`
- `data/processed/buildinghub_event_match_audit.csv`
- `data/processed/buildinghub_date_filter_semantics_summary.csv`
- `data/processed/buildinghub_source_final_status.json`

현재 D1 판정은 다음과 같다.

| item | status |
| --- | --- |
| selected_filter_rule | not_selected |
| source_status | blocked |
| nationwide row collection | prohibited |
| next action | operation inventory 또는 broad collection + event-date post-filtering 가능성 검토 |

## 건축HUB Operation Inventory

O1을 실행했다. 공공데이터포털의 `국토교통부_건축HUB_건축인허가정보 서비스` API 목록과 건축HUB Open API 안내를 기준으로 건축인허가 operation 17개를 inventory화하고, 각 endpoint에 대해 `sigunguCd=11680`, `bjdongCd=10300`, `numOfRows=1` 원칙으로 1행 probe를 수행했다.

| item | result |
| --- | --- |
| operation candidates | 17 |
| probe policy | endpoint별 1행, 대량 수집 없음 |
| successful probe responses | 17 |
| actual row operations | 17 |
| permit/start/approval-specific operation | not found |
| mixed event field operation | `getApBasisOulnInfo` |
| mixed event fields | `archPmsDay`, `realStcnsDay`, `useAprDay` |
| selected event-specific route | none |

`getApBasisOulnInfo`는 허가일·실제착공일·사용승인일 필드를 모두 포함하지만 D1에서 `startDate/endDate` 필터 의미 검증을 통과하지 못했다. 나머지 operation은 동별개요, 층별개요, 호별개요, 대수선, 전유공용면적, 공작물관리대장, 철거멸실관리대장, 가설건축물, 오수정화시설, 주차장, 부설주차장, 호별전유공용면적, 지역지구구역, 도로명대장, 대지위치, 주택유형 등 상세 속성 조회이며 permit/start/approval 전용 event endpoint로 보지 않는다.

Generated artifacts:

- `data/processed/buildinghub_operation_inventory.csv`
- `data/processed/buildinghub_event_endpoint_probe.csv`

## 건축HUB Event-specific Operation Inventory

Current decision: `event_specific_endpoint_found = false`.

공식 API 목록에는 `착공신고`, `실제착공`, `사용승인`, `허가취소`를 각각 독립적으로 조회하는 operation이 확인되지 않았다. 따라서 현재 단계에서는 event-specific API route를 선택하지 않는다. 다음 경로는 bulk historical route 확인 또는 broad collection + event-date post-filter pilot이다.

## 건축HUB Bulk Download Feasibility

B1을 실행했다. 건축HUB의 `원하는대로 건축데이터`, `대용량 제공 서비스`, 공공데이터포털 OpenAPI/표준데이터 페이지를 확인했다.

| item | result |
| --- | --- |
| checked pages | 4 |
| bulk route mention | yes |
| provided themes observed | 건축인허가, 건축물대장, 주택인허가, 건물에너지 등 |
| file formats observed | CSV, JSON, XLSX |
| monthly update signal | yes |
| login/member signal | yes |
| unauthenticated direct download confirmed | no |
| historical monthly vintage confirmed | no |
| historical archive usable for pipeline | not confirmed |

건축HUB 페이지는 대용량 데이터 제공 서비스가 존재하며, 운영 중인 세움터 현황 데이터를 월 단위로 생성한다는 신호를 제공한다. 또한 최근 월 대용량 데이터는 전월까지의 갱신데이터를 익월 20일 전후 제공한다는 설명이 확인된다. 다만 현재 자동 probe에서는 로그인 없이 직접 받을 수 있는 historical archive 파일 URL이나 월별 vintage 보존 구조를 확인하지 못했다.

Generated artifact:

- `data/processed/buildinghub_bulk_download_inventory.csv`

## 건축HUB Bulk Historical Route

Current decision: `historical_bulk_route = not_confirmed`.

대용량 route는 존재하지만 바로 production pipeline의 primary route로 전환할 수 없다. 이유는 다음과 같다.

- 직접 다운로드 URL이 확인되지 않았다.
- 과거 월별 vintage가 보존되는지 확인되지 않았다.
- 로그인 또는 회원 권한이 필요한 흐름으로 보인다.
- 파일별 공개시점과 revision policy가 아직 확인되지 않았다.

따라서 bulk route는 계속 우선 후보로 유지하되, 현재 단계에서는 `switch_to_bulk_pipeline` 판정을 내리지 않는다.

## 건축HUB Request Budget

이번 D1은 540개 제한 probe로 수행했다. 전국 실행은 여전히 금지한다. 현재 단순 월별 전국 totalCount inventory 예상치는 729,936회이며, D1 결과상 이 요청량을 감수할 만큼 event semantics가 확정되지 않았다.

O1/B1 이후에도 전국 실행은 금지한다. Event-specific endpoint가 없고 직접 historical bulk route도 확인되지 않았으므로, 다음 실험은 소규모 broad collection + event-date post-filter pilot이어야 한다. 이 pilot에서도 먼저 5개 지역·2023년·연간/반기/분기/월 query recall만 비교하고 전국으로 확장하지 않는다.

## 건축HUB Broad Collection Pilot

Not started. 실행 조건은 `event_specific_endpoint = not_found`와 `historical_bulk_route = not_available`이다. 현재 O1에서 event-specific endpoint는 찾지 못했지만, B1에서 bulk route는 존재 신호가 있으나 직접 archive가 미확인 상태다. 따라서 broad pilot은 다음 단계에서 수동 검토 또는 추가 bulk 접근 확인 후 진행한다.

## 건축 Event Post-filter Recall

Not started. Broad collection pilot을 실행한 뒤에만 연간·반기·분기·월별 query의 event recall을 비교한다. 기준 event date는 계속 `permit=archPmsDay`, `start=realStcnsDay`, `approval=useAprDay`로 유지하며, query 기간을 observation period로 직접 사용하지 않는다.

## 건축HUB Historical Vintage Feasibility

Not complete. 42개 필드 inventory에서는 `archPmsDay`, `realStcnsDay`, `useAprDay`, `crtnDay`가 날짜 후보로 확인됐다. 하지만 과거 event의 최초 공개일 또는 수정이력을 복원할 수 있는 필드는 아직 확인되지 않았으므로, retrieval date를 과거 publication date로 소급하지 않는다.

## 건축 주용도 Mapping

파일럿에서 17개 주용도 코드가 관측됐다. rule 기반 mapping의 pilot unknown purpose rate는 약 24.5%로 높다. 따라서 `buildinghub_purpose_code_inventory.csv`의 현재 rule은 development 후보일 뿐이고, 전체 observed code inventory와 공식 주용도 코드표를 결합해 `unknown_purpose_rate <= 0.05` 기준을 다시 평가한다.

## 건축HUB Purpose Mapping Final

Not complete. 현재 상위 관측 코드 기준 rule mapping은 존재하지만 최종 mapping이 아니다. D1에서 event semantics가 block 상태이므로 전국 row inventory를 확장하지 않았고, 전체 observed purpose code inventory도 아직 없다. 다음 단계에서는 공식 건축물 주용도 코드표와 결합해 `unknown_purpose_rate <= 0.05`, `unmapped_top_20_frequency_code = 0`을 검증한다.

## 건축 지역 Coverage

로컬 공식 법정동 코드표를 기준으로 `sigunguCd`/`bjdongCd` 기반 crosswalk 256개 시군구를 생성했다. 이는 sample `platPlc` 문자열 파싱보다 우선하는 공식 mapping이다. 다만 전국 건축HUB historical inventory와 official actual 모집단의 coverage 계산은 아직 완료되지 않았다.

## 건축 Publication Lag

`buildinghub_publication_lag_audit.csv`에 V0~V3 후보 규칙을 기록했다. 다만 monthly snapshot revision audit가 아직 baseline 이상으로 쌓이지 않았으므로 `publication_date`와 `first_eligible_period`는 구현하지 않는다.

## 건축 Feature Pilot

`buildinghub_feature_table.csv`는 846개 pilot feature row를 생성했지만 production feature table이 아니다. 이유는 두 가지다.

1. 반환 샘플 row의 날짜가 요청 월과 항상 정합적이지 않다.
2. `first_eligible_period`와 publication lag 정책이 아직 구현되지 않았다.

따라서 F00/L00 모델 학습에는 아직 사용할 수 없다. 다음 단계에서는 이벤트 날짜별 사후 필터링과 `first_eligible_period`를 적용한 뒤 feature table을 다시 생성한다.

## 건축HUB Nationwide Coverage

Not started. D1에서 event date filter rule이 확정되지 않았으므로 전국 annual screening, monthly positive inventory, row download를 실행하지 않는다. Coverage에서 `totalCount=0`은 query failure가 아니라 `true_zero` 후보로 분리해야 하며, 이 분류는 event extraction rule이 확정된 뒤 수행한다.

## 건축 Event-specific Feature Tables

Not generated. Production 원천 집계 단계에서는 permit, start, approval table을 분리해야 하지만, 현재는 `startDate/endDate`가 세 이벤트 중 어느 날짜를 엄격히 필터링하는지 확정되지 않았다.

Required future outputs:

- `buildinghub_permit_feature_table.csv`
- `buildinghub_start_feature_table.csv`
- `buildinghub_approval_feature_table.csv`

## 건축HUB Final Source Status

Current status: `blocked_pending_broad_collection_pilot`.

Reason: D1 event semantics gate failed, O1에서 permit/start/approval 전용 operation을 찾지 못했고, B1에서 비로그인 직접 historical bulk archive를 확인하지 못했다. 기본개요 endpoint의 `startDate/endDate`는 permit/start/approval 중 어떤 이벤트 날짜도 95% 기준으로 안정적으로 설명하지 못했다. 특히 approval은 가장 높은 target 반환율을 보였지만 90%로 기준에 미달했고, permit/start는 훨씬 낮았다.

Allowed next actions:

- 건축HUB 대용량 데이터 제공 화면에서 직접 파일 접근 가능 여부를 수동 확인한다.
- 수동 확인에서도 historical bulk archive가 없으면 5개 지역·2023년 broad collection pilot을 실행한다.
- broad collection 후 `archPmsDay`, `realStcnsDay`, `useAprDay`로 사후 필터링하는 방식의 recall과 traffic budget을 별도로 추정한다.

Prohibited actions:

- 전국 row 수집 시작
- 2021~2023 backtest용 건축HUB feature 사용
- retrieval date를 historical publication date로 소급
- D1 결과를 무시하고 production feature table 생성

## 서울 열린데이터 교차검증

`SEOUL_OPENAPI_KEY`는 `.env`에 존재하지만, 이번 단계에서는 건축HUB 파일럿 request universe와 historical inventory 생성에 집중했다. 서울 열린데이터는 전국 source가 아니라 validation pilot으로만 사용한다.

## 건축HUB ML-ready 최종 판정

| gate | status |
| --- | --- |
| Access | pass |
| Schema probe | pass |
| Request universe | pass for pilot / nationwide not probed |
| Historical inventory | pilot only |
| Region crosswalk | partial official crosswalk |
| Coverage | not complete |
| Purpose mapping | not complete |
| Publication lag | not complete |
| First eligible period | not implemented |
| Feature table | pilot only / blocked for production |
| Final status | blocked |

현재 차단 조건은 더 이상 법정동 코드표 부재가 아니다. 남은 blocker는 전국 historical inventory 규모, 이벤트 날짜 필터 정합성, 주용도 mapping 미완성, publication lag/first eligible period 미구현이다.

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
- 건축HUB는 로컬 공식 법정동 코드표를 확보해 `sigunguCd`, `bjdongCd` 기반 crosswalk로 교체했다. `platPlc` 문자열 파싱 crosswalk는 sample 보조 진단으로만 유지한다.
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

1. 건축HUB `startDate`/`endDate`가 어떤 이벤트 날짜를 필터링하는지 공식 문서와 추가 probe로 확정한다.
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

## Phase 0 Structural Source Gate

최신 Phase 0 판정은 `reports/structural_feature_phase0_readiness.md`에 별도 정리했다. 현재 ML 재개 판단은 `blocked_no_ml_ready_structural_source`이며, 전력 feature는 standalone correction이 아니라 structural source 통과 이후의 interaction/auxiliary 변수로만 유지한다.
