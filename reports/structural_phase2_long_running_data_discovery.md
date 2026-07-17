# Structural Feature Phase 2

## 1. 실행 요약

Phase 2는 모델 학습 없이 공식 원천자료 탐색, historical reconstruction 가능성, 대용량 파일/공간자료 readiness를 점검했다. FactoryOn 일반자료실은 pagination과 상세 게시글을 캐시하며 전수 inventory했고, 공공데이터포털 파일형 자료는 `contentUrl`을 우선 사용해 가능한 파일을 다운로드했다.

대형 workbook은 운영 재개 가능성을 위해 전 행 순회 대신 전체 행수 metadata와 제한 행 스캔을 분리했다. 따라서 이번 산출물은 ML 학습용 feature가 아니라 `source discovery`, `schema/period audit`, `manual-action queue`에 해당한다.

- restart_decision: `blocked_no_ml_ready_structural_source`
- new_ml_training: `prohibited`
- factoryon_posts: `207`
- factoryon_attachments: `207`
- factoryon_downloaded_attachments: `4`
- data_go_downloaded_files: `4`
- user_action_open_count: `2`

## 2. Phase 1 상태

Phase 1에서 공장 주소 crosswalk는 1% 이하 기준을 통과했지만, 2021-2023 historical stock과 공식 KSIC mapping이 없어 ML-ready는 아니었다. 이 판단은 유지된다.

## 3. FactoryOn 자료실 Inventory

- board rows: `207`
- attachment rows: `207`
- downloaded target attachments: `4`
- 다운로드된 FactoryOn 첨부는 산업단지 맥락자료와 서식 중심이었다. 전국 등록공장 2021-2023 historical snapshot 원문은 자동 inventory에서 확보되지 않았다.

## 4. 공장 Historical Snapshot Coverage

- historical snapshot inventory rows: `0`
- 2021/2022/2023 snapshot이 모두 확보되지 않으면 공장등록 Source는 `blocked_missing_history`다.

## 5. 공장 Key Stability 및 Flow 가능성

공장관리번호가 안정적인 Snapshot 쌍에서만 flow를 만들 수 있다. Snapshot 소실은 폐쇄로 단정하지 않고 `unknown_not_closure_without_validation`으로 기록한다.

## 6. KSIC 10차·11차 Crosswalk

공식 KSIC 10차·11차 연계표는 아직 파싱 완료되지 않았다. 관측 공장 KSIC mapping audit은 unresolved 상태로 남겼고, one-to-many mapping을 임의 축약하지 않는다.

## 7. 산업단지별 공장데이터 대용량 감사

- largefile schema rows: `7`
- largefile period rows: `99`
- workbook scan limit: `50000` rows per sheet
이 파일은 공장등록 개별 stock이 아니라 산업단지 집계/stock 후보로 분리해 판정한다.

## 8. 산업단지 Historical Activity 수집

산업동향 API는 endpoint/parameter 문서화가 먼저라 반복 오류 요청을 피하기 위해 operation x period probe manifest만 생성했다.

## 9. 산업단지 공식 코드 Mapping

공식 단지코드 registry와 명칭 crosswalk는 아직 incomplete다. 단지명을 공식 코드로 간주하지 않는다.

## 10. 산업단지 Polygon

- industrial polygon inventory rows: `1`
SHP가 확보되어도 geometry parser와 시군구 polygon intersection이 끝나기 전에는 allocation을 확정하지 않는다.

## 11. 시군구 Geometry

- boundary inventory rows: `40`
경계 파일은 다운로드/ZIP inventory 단계이며, geometry audit/repair/graph 생성을 완료하려면 geometry parser가 필요하다.

## 12. Spatial Graph

Queen/Rook/Distance graph는 아직 통과하지 않았다. 도서지역에 임의 adjacency를 추가하지 않는다.

## 13. 산업단지-시군구 Allocation

대표주소 전량 배정은 금지한다. Polygon intersection 또는 기업/고용/산업시설면적 weight가 확보될 때까지 allocation은 unresolved다.

## 14. 한국형 Geography Feature 갱신

Phase 1 rule registry는 유지된다. Phase 2에서는 공식 geometry가 준비되기 전까지 source-required feature를 임의 값으로 채우지 않았다.

## 15. 사용자 개입 요청

- open requests: `2`
- `data/processed/structural_phase2_user_action_requests.csv`에 공식 URL, 필요한 수동 조치, 저장 위치를 기록했다.
- 현재 open 항목은 FactoryOn 2021-2023 전국 등록공장 원본과 산업단지 토지이용 원문이다.

## 16. Source Gate Matrix

`data/processed/structural_phase2_source_gates.csv` 참조.

## 17. ML-ready 판정

최소 하나의 structural source와 spatial gate가 아직 동시에 통과하지 못했으므로 ML-ready source는 없다.

## 18. Bundle Eligibility

`data/processed/structural_phase2_bundle_registry.csv` 참조. 모든 challenger bundle은 학습 금지 상태다.

## 19. ML Restart 결정

`blocked_no_ml_ready_structural_source`. Ridge/ElasticNet도 실행하지 않는다.

## 20. 다음 실행 항목

1. FactoryOn에서 누락된 2021-2023 원본 첨부를 수동 확보하거나 추가 검색 조건을 확장한다.
2. KSIC 10차·11차 공식 연계표를 다운로드해 관측 공장 업종코드 mapping rate를 계산한다.
3. SGIS/산업단지 SHP를 geometry parser로 처리해 centroid와 Queen/Rook/Distance graph를 생성한다.
4. 산업단지 polygon과 시군구 polygon intersection으로 allocation weight를 만든다.
5. 산업동향 API operation별 1행 probe를 문서 기준으로 실행한 뒤 2021-2023 분기 activity를 수집한다.
