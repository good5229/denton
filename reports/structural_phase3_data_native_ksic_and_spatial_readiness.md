# Structural Feature Phase 3

## 1. 실행 요약

- 실행시각: `2026-07-18T00:43:23`
- KSIC Gate: `blocked_mapping_quality`
- Spatial Gate: `pass`
- Industrial Allocation Gate: `blocked_geometry_source`
- ML restart: `blocked_user_action_required`. 이번 Phase에서는 모델을 학습하지 않았다.

## 2. Phase 2 상태

Phase 2의 `blocked_no_ml_ready_structural_source`에서 시작했다. Phase 3은 확보한 원천을 끝까지 파싱하는 기반 작업이며, 같은 Actual에 대한 재튜닝은 수행하지 않았다.

## 3. 로컬 Source Inventory

- 파일 `3,763`개와 archive member `363`개를 hash 기반으로 목록화했다.

| source type | files |
| --- | ---: |
| factory_snapshot | 468 |
| industrial_complex_boundary | 5 |
| industrial_complex_statistics | 27 |
| ksic_code_table | 6 |
| ksic_crosswalk | 2 |
| legal_dong_code | 13 |
| sigungu_boundary | 1 |
| unknown_candidate | 3,241 |

## 4. 공장 관측 KSIC Inventory

- 관측 코드 집계 `5,070`행, 공장-코드 원행 `198,235`행을 처리했다.
- KSIC 코드는 문자열로 유지했으며 leading zero를 보존했다. 복수코드의 첫 항목을 대표업종으로 추정하지 않았다.

## 5. KSIC 10차·11차 공식 Crosswalk

- 국가데이터처 공식 XLSX에서 KSIC 10 registry `1,196`개, KSIC 11 registry `1,205`개, 관계 `1,231`행을 생성했다.
- One-to-many는 행을 유지하고 공식 weight가 없으면 `mapping_weight=null`, `deterministic_fine_mapping=N`으로 남겼다.

## 6. 공장 KSIC Mapping Coverage

| metric | result | gate |
| --- | ---: | --- |
| observed row mapping | 98.9124% | fail |
| employee-weighted mapping | 98.3612% | fail |
| unknown KSIC version | 0.0938% | pass |
| unresolved codes | 496 | target 0 |

명시적으로 8차·9차인 행을 코드가 같다는 이유만으로 10차로 소급하지 않았다. 따라서 현재 KSIC Gate는 공식 8/9→10 근거가 추가되기 전까지 보수적으로 차단된다.

## 7. KSIC 수동검토 Queue

- 자동 매핑이 해결하지 못한 코드 `496`개만 별도 queue에 보존했다. 원본 산출물은 덮어쓰지 않았다.

## 8. 시군구 Boundary Layer

- SGIS 2025Q2 시군구 layer: 원경계 `252`개, 모델 평가 universe `228`개.
- 원본 CRS `EPSG:5179`, 면적·거리 CRS `EPSG:5179`, 배포 좌표 확인용 CRS `EPSG:4326`.

## 9. Geometry Quality 및 Repair

- Repair 후 invalid `0`, empty `0`, 최대 면적변화율 `0.000000%`.
- 원본·수정 geometry hash와 면적을 feature별 audit에 보존했다.

## 10. 시군구 Crosswalk

- Official Actual 모델지역 matched `228`, unmatched `0`.
- 일반구 보유 도시는 자치구 polygon union, 세종·군위는 historical alias로 기록했다.

## 11. Centroid 및 대표점

- `228`개 지역에 geometric centroid와 polygon 내부 representative point를 모두 생성했다. 거리 계산에는 대표점을 고정 사용했다.

## 12. Queen/Rook Graph

- Queen directed edges `1,156`, Rook directed edges `1,154`. Rook 최소 공유경계는 `1.0m`로 사전 고정했다.

| graph | nodes | directed edges | isolated | asymmetry | status |
| --- | ---: | ---: | ---: | ---: | --- |
| queen | 228 | 1156 | 8 | 0 | pass |
| rook | 228 | 1154 | 8 | 0 | pass |

## 13. Distance Graph

Nearest-3/5와 50km/100km threshold graph를 분리 생성했다. Threshold graph는 진단용이며 모델 후보로 자동 채택하지 않는다.

| graph | edges | isolated | status |
| --- | ---: | ---: | --- |
| nearest_3 | 902 | 0 | pass |
| nearest_5 | 1448 | 0 | pass |
| distance_threshold_50km | 5206 | 2 | pass |
| distance_threshold_100km | 12316 | 2 | pass |

## 14. 산업단지 Geometry

- 상태: `blocked_geometry_source`. official VWorld DAM_PDAN.zip was not obtainable automatically; cached candidates are HTML or empty

## 15. 산업단지-시군구 Intersection

- intersection rows: `0`. Polygon 원본이 유효할 때만 공간교차를 수행한다.

## 16. Allocation Weight

- allocation pass: `0/0`. 대표주소 전량배정은 사용하지 않았다.

## 17. Historical Source 추가 탐색

- FactoryOn 2021~2023 전국 snapshot은 계속 open 상태다.
- 산업동향 API는 공식 operation·필수 parameter가 확정되지 않아 1행 probe를 반복 실행하지 않았다.

## 18. 사용자 개입 요청

| priority | source | required file | target |
| ---: | --- | --- | --- |
| 1 | KSIC 8차·9차에서 10차로의 공식 연계표 | KSIC 8-9-10 official crosswalk XLSX | `data/raw/ksic/` |
| 3 | 브이월드 산업단지 공간정보 SHP | DAM_PDAN.zip | `data/raw/structural_phase3/manual/DAM_PDAN.zip` |
| 4 | FactoryOn 2021-2023 전국 공장등록 Historical Snapshot | 2021/2022/2023 national factory snapshot | `data/raw/structural_phase2/factoryon/manual/` |

비밀번호, 인증키 원문, 개인 로그인정보는 전달하지 않는다.

## 19. KSIC Gate

- `blocked_mapping_quality`: row=0.989124019471839; employee=0.9836124204488702; unresolved=50

## 20. Spatial Gate

- `pass`: 공식 모델지역 전수 geometry와 그래프 audit 기준으로 판정했다.

## 21. Industrial Allocation Gate

- `blocked_geometry_source`: official VWorld DAM_PDAN.zip was not obtainable automatically; cached candidates are HTML or empty

## 22. Structural Source Gate Matrix

| source | status | detail |
| --- | --- | --- |
| ksic | blocked_mapping_quality | row=0.989124019471839; employee=0.9836124204488702; unresolved=50 |
| spatial_graph | pass |  |
| industrial_complex_allocation | blocked_geometry_source | official VWorld DAM_PDAN.zip was not obtainable automatically; cached candidates are HTML or empty |
| factory_registration_history | blocked_missing_history | 2021-2023 national snapshots required |
| industrial_complex_activity | blocked_missing_history | official one-row API probe and 2021Q1-2023Q4 positive period cache incomplete |

## 23. ML Restart 결정

- `blocked_user_action_required`
- 최소 하나의 structural source가 ML-ready이고 publication date, first eligible period, frozen bundle, preregistration이 모두 구현되기 전에는 Ridge·ElasticNet·XGBoost를 실행하지 않는다.

## 24. 다음 실행 항목

1. KSIC 8차·9차 공식 연계표 또는 검토된 override로 공장 행·종업원 가중 mapping 99%와 상위 미해결 0건을 충족한다.
2. 브이월드 `DAM_PDAN.zip` 원본을 확보해 산업단지 코드·geometry·시군구 intersection을 재실행한다.
3. 2021~2023 전국 공장 snapshot과 산업단지 activity history를 확보한 뒤 publication lag와 first eligible period를 확정한다.
4. 그 뒤에만 structural bundle을 동결·사전등록하고 ML 재개 여부를 판단한다.
