# Phase258 건설업 대체 공개자료 자료준비도 감사

생성시각: 2026-07-29T19:04:51+09:00

## 1. 목적

Phase257 no-raw smoke에서도 PPS 공사계약·공사공고 API가 `HTTP 429`로 막혔다. 이번 감사는 이미 로컬에 수집된 BuildingHUB·CALS·LH·서울 정비사업·PPS 부분자료가 건설업 시군구 GVA 배분 개선에 어느 정도 준비되어 있는지 점검한다. 새 route를 채택하거나 성능개선을 주장하지 않는다.

## 2. 자료별 readiness 판정

| source_block | coverage_label | signal_type | best_use | route_readiness | main_blocker |
| --- | --- | --- | --- | --- | --- |
| BuildingHUB 건축물 인허가·착공·사용승인 | limited_priority_city_or_partial_historical | 면적·건수·용도별 이벤트 | 민간건축형 도시의 구조 진단 및 refinement 후보 | diagnostic_only | 전국 전기간 완전성·공표시점/vintage·금액형 자료 부족 |
| CALS 공사목록/계약 | public_soc_snapshot | 공공/SOC 공사 금액·기간 일부 | 도로·하천·토목형 지역 보조 신호 | not_route_ready | 민간건설 미포착, 전국 GVA 전체 대체 불가 |
| LH 분양·임대 공고 | 2021_2023_notice_events | 공공주택·토지 공고건수 | 공공주택 이벤트 진단 | rejected_by_guardrail | 금액형 기성/투자액 부재, Phase246 safe 후보 0개 |
| 서울 도시정비사업 | seoul_only_snapshot | 정비사업 단계·세대수 | 서울 재개발·재건축형 구 보조 | local_only | 전국 자료 아님, 서울 외 일반화 불가 |
| PPS 공사공고/계약 | partial_complete_months_or_api_blocked | 공공공사 예산·계약금액 | 공공·토목형 보조 신호 | blocked_by_429_and_partial_coverage | Phase257 429, 완전월/완전연도 부족, 공공공사 편향 |

## 3. 로컬 파일 인벤토리

| source_id | exists | rows | columns | tracked_role |
| --- | --- | --- | --- | --- |
| buildinghub_feature_table | True | 846 | 7 | 민간건축 면적·건수 보조 |
| buildinghub_monthly_total_count | True | 27 | 6 | 민간건축 면적·건수 보조 |
| buildinghub_request_manifest | True | 9 | 17 | 민간건축 면적·건수 보조 |
| buildinghub_priority_top5_features | True | 600 | 5 | 민간건축 면적·건수 보조 |
| cals_contract_rows | True | 1,683 | 34 | 공공/SOC 공사 보조 |
| cals_contract_list | True | 1,359 | 21 | 공공/SOC 공사 보조 |
| lh_notice_rows | True | 9,465 | 18 | 공공주택·토지 공고 이벤트 |
| seoul_redevelopment_summary | True | 142 | 5 | 서울 정비사업 단계·세대수 |
| phase244_candidate_summary | True | 73 | 10 | 기존 후보 route 검증 결과 |
| phase244_guardrail_safe | True | 5 | 12 | 기존 후보 route 검증 결과 |
| phase245_policy_summary | True | 2 | 8 | 기존 후보 route 검증 결과 |
| phase246_lh_candidate_summary | True | 8 | 9 | 기존 후보 route 검증 결과 |
| phase246_lh_guardrail_safe | True | 0 | 9 | 기존 후보 route 검증 결과 |
| construction_error_by_city | True | 229 | 13 | 건설업 오차 진단 |
| construction_error_top_cells | True | 50 | 15 | 건설업 오차 진단 |

## 4. coverage 요약

| source_id | observation_period_min | observation_period_max | observation_period_nunique | rows | request_month_min | request_month_max | request_month_nunique | year_min | year_max | year_nunique | province_full_nunique | city_nunique | contract_year_min | contract_year_max | contract_year_nunique | stwrDt_min | stwrDt_max | stwrDt_nunique | ccwDt_min | ccwDt_max | ccwDt_nunique | source_period_min | source_period_max | source_period_nunique | PAN_NT_ST_DT_min | PAN_NT_ST_DT_max | PAN_NT_ST_DT_nunique | PAN_DT_min | PAN_DT_max | PAN_DT_nunique | CNP_CD_NM_nunique | actual_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buildinghub_feature_table | 200006 | 202312 | 81.0 | 846 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| buildinghub_monthly_total_count |  |  |  | 27 | 202101 | 202312 | 9.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| buildinghub_request_manifest |  |  |  | 9 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| buildinghub_priority_top5_features |  |  |  | 600 |  |  |  | 2019 | 2023 | 5.0 | 3.0 | 5.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| cals_contract_rows |  |  |  | 1,683 |  |  |  |  |  |  |  |  | 1997 | 2027 | 31.0 | 1996-08-26 | 2025-09-01 | 217.0 | 2004-08-13 | 2031-10-25 | 225.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| cals_contract_list |  |  |  | 1,359 |  |  |  |  |  |  |  |  |  |  |  | 1995-09-29 | 2026-06-30 | 883.0 | 2003-12-25 | 2034-12-30 | 885.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| lh_notice_rows |  |  |  | 9,465 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 202101 | 202312 | 35.0 | 2021.01.04 | 2023.12.29 | 726.0 | 20200615.0 | 20240415.0 | 716.0 | 24.0 |  |  |  |  |  |  |
| seoul_redevelopment_summary |  |  |  | 142 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| phase244_candidate_summary |  |  |  | 73 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2985125.439957481 | 572409.352861647 | 19.17538691003217 | 358.0 | 222.0 | 356.98142374332963 |
| phase244_guardrail_safe |  |  |  | 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2985125.439957481 | 575423.0501552204 | 19.276344050835483 | 360.0 | 224.0 | 274.84099023007525 |
| phase245_policy_summary |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2985125.439957481 | 579987.7583035273 | 19.4292591708236 | 361.0 | 224.0 | 294.56946340007926 |
| phase246_lh_candidate_summary |  |  |  | 8 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2985125.439957481 | 579987.7583035273 | 19.4292591708236 | 361.0 | 224.0 | 294.56946340007926 |
| phase246_lh_guardrail_safe |  |  |  | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| construction_error_by_city |  |  |  | 229 |  |  |  |  |  |  | 17.0 | 207.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 156421.84 | 26069.34584143573 | 16.666052414059145 | 2.0 | 1.0 | 24.642603387907947 |
| construction_error_top_cells |  |  |  | 50 |  |  |  | 2021 | 2023 | 3.0 | 9.0 | 33.0 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

주의: CALS의 `ccwDt`·`ccwXpcDt` 계열에는 준공일 또는 준공예정일 성격의 미래 날짜가 포함될 수 있다. 따라서 coverage 표의 미래 최대일자는 수집시점 이후의 실제 관측기간 확장이 아니라 공사 예정·계획 기간 정보로 해석한다.

## 5. 기존 후보 실험 성능 레지스트리

| experiment | baseline_wape_pct | best_or_selected_wape_pct | wape_delta_pp | baseline_over10_cells | candidate_over10_cells | baseline_max_ape_pct | candidate_max_ape_pct | safe_candidate_count | route_adoption | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase244_multi_source | 19.429 | 19.175 | -0.254 | 361.000 | 358.000 | 294.569 | 356.981 | 5 | not_adopted | 탐색 결과 일부 safe 후보 있으나 rolling 채택 전 단계 |
| phase245_rolling_city_gate | 19.429 | 19.446 | 0.016 | 361.000 | 362.000 | 294.569 | 290.624 | 0 | not_adopted | rolling 적용 결과 기준보다 WAPE 악화 |
| phase246_lh_augmented | 19.429 | 19.429 | 0.000 | 361.000 | 361.000 | 294.569 | 294.569 | 0 | not_adopted | LH 단독/미세혼합 safe 후보 없음 |

## 6. 건설업 잔여오차 상위 시군구

| province_full | city | years | actual_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 경기도 | 평택시 | 3 | 156,421.84 | 26,069.35 | 16.67 | 2 | 1 | 24.64 |
| 서울특별시 | 강남구 | 3 | 45,541.73 | 25,101.11 | 55.12 | 3 | 2 | 148.63 |
| 서울특별시 | 영등포구 | 3 | 32,101.59 | 23,686.87 | 73.79 | 3 | 3 | 120.67 |
| 서울특별시 | 강서구 | 3 | 33,915.13 | 15,831.79 | 46.68 | 2 | 2 | 77.72 |
| 전라남도 | 여수시 | 3 | 58,259.97 | 14,353.09 | 24.64 | 2 | 2 | 33.09 |
| 인천광역시 | 서구 | 3 | 73,465.53 | 14,314.96 | 19.49 | 2 | 2 | 29.91 |
| 서울특별시 | 서초구 | 3 | 25,933.95 | 13,039.73 | 50.28 | 3 | 2 | 107.93 |
| 서울특별시 | 용산구 | 3 | 16,739.40 | 12,619.17 | 75.39 | 3 | 3 | 103.92 |
| 경기도 | 이천시 | 3 | 42,085.96 | 10,785.19 | 25.63 | 2 | 1 | 70.39 |
| 충청북도 | 청주시 | 3 | 62,043.73 | 10,024.25 | 16.16 | 1 | 1 | 31.14 |

## 7. 누수·과잉주장 위험

| risk | description | mitigation |
| --- | --- | --- |
| snapshot_vintage_leakage | 2026년 수집 snapshot을 과거 속보 route처럼 쓰는 위험 | retrieved_at/source_period 기준 분리, strict nowcast에서는 제외 |
| private_construction_undercoverage | PPS/CALS/LH가 민간 주거·상업·산업건축을 충분히 포착하지 못함 | 민간건축형·공공토목형 지역유형 gate 사전 정의 |
| money_proxy_gap | BuildingHUB/LH/정비사업은 건수·면적·단계 중심으로 GVA 금액형 proxy가 약함 | 금액형 계약/기성/착공예정액 확보 전 단독 route 금지 |
| spatial_attribution_error | 기관명·공고명 텍스트 기반 지역귀속은 실제 공사 수행지와 다를 수 있음 | 위치 필드 우선, confidence tier와 매칭률 gate 적용 |
| same_cell_selection_leakage | 오차 큰 도시를 보고 후보를 붙인 뒤 같은 도시·연도에서 성능 주장 | discovery/holdout city 또는 out-of-year rolling 검증 |

## 8. 운영 판정

1. BuildingHUB는 민간건축형 도시의 구조 진단에는 필요하지만, 현재 로컬 범위와 snapshot/vintage 한계 때문에 전국 2015~2025 건설업 route로 채택하지 않는다.
2. CALS와 PPS는 공공·토목형 보조 신호다. 민간 건설업 전체 GVA를 대표한다고 쓰면 안 된다.
3. LH는 2021~2023 공공주택·토지 공고 이벤트로 의미가 있지만, Phase246에서 guardrail safe 후보가 0개였으므로 단독 route로 채택하지 않는다.
4. 서울 도시정비사업은 서울 재개발·재건축형 구의 보조자료다. 전국 일반화 근거가 아니다.
5. 다음 성능개선은 자료별 단독 route가 아니라 지역유형 gate를 사전 고정한 뒤 `민간건축형(BuildingHUB)`, `공공·토목형(PPS/CALS)`, `공공주택형(LH)`, `정비사업형(지자체 정비사업)`을 분리해 rolling holdout으로 검증해야 한다.

## 9. route 승격 최소조건

- 2015~2025 또는 명시된 검증기간의 전월/전분기 completeness 통과.
- target-year actual을 보지 않은 사전 route·가중치·지역유형 gate 고정.
- 기준선 대비 WAPE 개선, 10% 초과 셀·20% 초과 셀·최대 APE·대형 actual 셀 절대오차 비악화.
- 공표시점 또는 최소 retrieved_at/source_period 기준 명시.
- 공공자료를 전체 민간+공공 건설업 GVA actual로 표현하지 않는 해석 제한.

## 10. 산출물

- `nationwide/outputs/phase258_construction_alt_source_file_inventory.csv`
- `nationwide/outputs/phase258_construction_alt_source_coverage_summary.csv`
- `nationwide/outputs/phase258_construction_alt_source_performance_registry.csv`
- `nationwide/outputs/phase258_construction_alt_source_readiness_registry.csv`
- `nationwide/outputs/phase258_construction_alt_source_risk_register.csv`
