# Phase261 건설업 지역유형 gate 다중자료 rolling 진단

생성시각: 2026-07-29T21:14:17+09:00

## 1. 목적

PPS 공사계약·공사공고 전량 수집이 `HTTP 429`로 막힌 상태에서, 이미 로컬에 수집된 CALS·서울 정비사업·BuildingHUB 신호만으로 건설업 시군구 배분을 안정적으로 개선할 수 있는지 점검한다. 이 실험은 route 채택이 아니라 retrospective rolling diagnostic이다.

## 2. 누수방지 설계

| 항목 | 설정 |
| --- | --- |
| 입력 | Phase244 candidate detail 재사용. 새 raw 수집 없음 |
| 검증 범위 | 2021~2023 건설업 시군구×연간 GVA actual 공표 셀 |
| parent total | Phase244의 시도 건설업 actual 총량 control 유지. strict nowcast 성능 아님 |
| 선택 규칙 | 2022는 2021 성과만, 2023은 2021~2022 성과만으로 지역유형×후보 선택 |
| 지역유형 | 다중신호, 서울 정비사업 양수, BuildingHUB 양수, CALS 양수 |
| guardrail | 훈련연도 WAPE·10%·20%·대형 actual 10%·max APE 모두 baseline 비악화 |
| 최소 표본 | 지역유형별 훈련 5셀 이상, 3개 시군구 이상 |
| fallback | 지역유형 gate 미통과 또는 신호 미적용 셀은 baseline 유지 |

## 3. 지역유형 coverage

| regime | rows | cities | years | actual_sum_eok | baseline_wape_pct |
| --- | --- | --- | --- | --- | --- |
| multi_source_positive | 3 | 2 | 2 | 105,688.160 | 14.238 |
| seoul_redevelopment_positive | 11 | 9 | 2 | 56,865.280 | 64.440 |
| buildinghub_positive | 15 | 5 | 3 | 326,240.260 | 28.874 |
| cals_positive | 56 | 31 | 3 | 370,580.730 | 13.018 |

## 4. 지역유형별 rolling 선택

| holdout_year | train_years | regime | selected_scenario | selection_reason | train_rows | train_cities | train_wape_pct | baseline_train_wape_pct | train_over10_cells | baseline_train_over10_cells | train_max_ape_pct | baseline_train_max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 2021 | multi_source_positive | baseline_parent_control | fallback_sparse_train_regime | 1 | 1.000 | 5.230 | 5.230 | 0.000 | 0.000 | 5.230 | 5.230 |
| 2022 | 2021 | seoul_redevelopment_positive | baseline_parent_control | no_train_regime_cells | 0 |  |  |  |  |  |  |  |
| 2022 | 2021 | buildinghub_positive | baseline_parent_control | fallback_no_regime_safe_candidate | 5 | 5.000 | 13.375 | 13.375 | 3.000 | 3.000 | 54.381 | 54.381 |
| 2022 | 2021 | cals_positive | baseline_parent_control | fallback_no_regime_safe_candidate | 26 | 26.000 | 11.520 | 11.520 | 10.000 | 10.000 | 89.249 | 89.249 |
| 2023 | 2021,2022 | multi_source_positive | baseline_parent_control | fallback_sparse_train_regime | 1 | 1.000 | 5.230 | 5.230 | 0.000 | 0.000 | 5.230 | 5.230 |
| 2023 | 2021,2022 | seoul_redevelopment_positive | baseline_parent_control | fallback_no_regime_safe_candidate | 5 | 5.000 | 72.935 | 72.935 | 5.000 | 5.000 | 157.167 | 157.167 |
| 2023 | 2021,2022 | buildinghub_positive | baseline_parent_control | fallback_no_regime_safe_candidate | 10 | 5.000 | 26.827 | 26.827 | 8.000 | 8.000 | 129.814 | 129.814 |
| 2023 | 2021,2022 | cals_positive | baseline_parent_control | fallback_no_regime_safe_candidate | 46 | 30.000 | 11.901 | 11.901 | 19.000 | 19.000 | 89.249 | 89.249 |

## 5. 연도별 holdout 결과

| year | rows | active_cells | baseline_wape_pct | selected_wape_pct | wape_delta_pp | baseline_over10_cells | selected_over10_cells | baseline_over20_cells | selected_over20_cells | baseline_large_actual_over10_cells | selected_large_actual_over10_cells | baseline_max_ape_pct | selected_max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 229 | 0 | 13.415 | 13.415 | 0.000 | 117 | 117 | 60 | 60 | 97 | 97 | 89.249 | 89.249 |
| 2022 | 229 | 0 | 22.272 | 22.272 | 0.000 | 149 | 149 | 94 | 94 | 124 | 124 | 294.569 | 294.569 |
| 2023 | 149 | 0 | 23.703 | 23.703 | 0.000 | 95 | 95 | 70 | 70 | 79 | 79 | 128.715 | 128.715 |

## 6. 전체 성능

| scenario | rows | actual_sum_eok | predicted_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells | max_ape_pct | active_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_parent_control | 607 | 2,985,125.440 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 300 | 294.569 | 0 |
| regime_gated | 607 | 2,985,125.440 | 2,985,125.440 | 579,987.758 | 19.429 | 361 | 224 | 300 | 294.569 | 0 |

## 7. 적용 셀 예시

_해당 없음_

## 8. 판정

1. PPS 없이 사용 가능한 대체자료 신호는 coverage가 좁다. CALS 양수는 31개 도시, 서울 정비사업은 9개 구, BuildingHUB는 5개 도시 수준이다.
2. 지역유형 gate는 같은 목표연도 actual을 보고 후보를 고르지 않지만, 입력 parent total이 사후 시도 actual control이므로 strict 속보 route가 아니다.
3. rolling 결과가 baseline guardrail을 통과하지 못하거나 적용 셀이 매우 제한적이면 건설업 전국 route로 채택하지 않는다.
4. 건설업 10% 목표 달성에는 PPS 계약/공고 완전월·민간건축 장기 금액형 자료·전국 정비사업 이력이 계속 필요하다.

## 9. 산출물

- `nationwide/outputs/phase261_construction_regime_gate_selection.csv`
- `nationwide/outputs/phase261_construction_regime_gate_selected_detail.csv`
- `nationwide/outputs/phase261_construction_regime_gate_overall_summary.csv`
- `nationwide/outputs/phase261_construction_regime_gate_holdout_summary.csv`
- `nationwide/outputs/phase261_construction_regime_gate_coverage.csv`
