# Phase259 광업·제조업 전력 share holdout 검증

생성시각: 2026-07-29T20:52:46+09:00

## 1. 목적

Phase256에서 광업·제조업 tail의 자료준비도는 확인했지만 route는 채택하지 않았다. 이번 실험은 2021~2023 공개 actual 구간에서 시군구별 산업용 전력 share가 기존 광업·제조업 공간배분을 개선하는지 rolling holdout으로 점검한다. 새 route를 채택하지 않는다.

## 2. 누수 방지 설계

| 항목 | 설정 |
| --- | --- |
| 대상 | `광업, 제조업` 시군구×연간 GVA, 2021~2023 |
| primary parent total | 기존 baseline의 시도×연도 예측 합계 유지 |
| 금지 | target 시군구 actual 합계로 province-year parent를 재주입해 성능 주장 금지 |
| 후보식 | `baseline_weight × 기존 share + (1-baseline_weight) × 산업용 전력 share` |
| grid | `1.00, 0.75, 0.50, 0.25, 0.00` |
| rolling 선택 | 2021→2022, 2021~2022→2023. 훈련연도에서 WAPE·10%·20%·대형 actual 10%·max APE 모두 비악화일 때만 후보 선택 |
| 공장등록 | 현재 snapshot 성격이므로 성능 route가 아니라 coverage 진단만 수행 |

## 3. coverage

| year | validation_cells | province_count | city_count | electricity_full12_cells | electricity_leakage_ok12_cells | actual_sum_eok | baseline_predicted_sum_eok | primary_parent_sum_eok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 229 | 17 | 207 | 229 | 229 | 5,658,407.51 | 5,658,407.45 | 5,658,407.45 |
| 2022 | 229 | 17 | 207 | 229 | 229 | 5,807,028.88 | 5,795,412.54 | 5,795,412.54 |
| 2023 | 149 | 11 | 143 | 149 | 149 | 4,035,828.90 | 4,066,324.13 | 4,066,324.13 |

## 4. 공장등록 snapshot 진단

| year | validation_cells | cells_with_factory | factory_rows | factory_employee_sum | factory_mfg_area_sum |
| --- | --- | --- | --- | --- | --- |
| 2021 | 229 | 229 | 198,167 | 3,736,055 | 278,543,378.27 |
| 2022 | 229 | 229 | 198,167 | 3,736,055 | 278,543,378.27 |
| 2023 | 149 | 149 | 142,377 | 2,504,424 | 175,461,515.89 |

## 5. 전체기간 후보 성능 탐색표

이 표는 discovery용이다. 같은 기간 전체 actual로 최선 후보를 고른 것이므로 route 채택 근거가 아니다.

| scenario | rows | actual_sum_eok | predicted_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| electricity_share_baseline_weight_1.00 | 607 | 15,501,265.286 | 15,520,144.122 | 882,479.816 | 5.693 | 172 | 45 | 122 | 212.492 |
| electricity_share_baseline_weight_0.75 | 607 | 15,501,265.286 | 15,520,144.122 | 1,745,218.095 | 11.259 | 333 | 168 | 263 | 707.775 |
| electricity_share_baseline_weight_0.50 | 607 | 15,501,265.286 | 15,520,144.122 | 3,165,931.553 | 20.424 | 432 | 296 | 352 | 1,205.962 |
| electricity_share_baseline_weight_0.25 | 607 | 15,501,265.286 | 15,520,144.122 | 4,652,009.106 | 30.011 | 491 | 370 | 400 | 1,791.517 |
| electricity_share_baseline_weight_0.00 | 607 | 15,501,265.286 | 15,520,144.122 | 6,151,564.507 | 39.684 | 517 | 430 | 420 | 2,377.073 |

## 6. rolling holdout 결과

| holdout_year | train_years | selected_scenario | selection_reason | baseline_wape_pct | selected_wape_pct | wape_delta_pp | baseline_over10_cells | selected_over10_cells | baseline_over20_cells | selected_over20_cells | baseline_large_actual_over10_cells | selected_large_actual_over10_cells | baseline_max_ape_pct | selected_max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 2021 | electricity_share_baseline_weight_1.00 | fallback_no_nonbaseline_train_safe_candidate | 5.535 | 5.535 | 0.000 | 50 | 50 | 10 | 10 | 37 | 37 | 44.751 | 44.751 |
| 2023 | 2021,2022 | electricity_share_baseline_weight_1.00 | fallback_no_nonbaseline_train_safe_candidate | 5.467 | 5.467 | 0.000 | 47 | 47 | 13 | 13 | 36 | 36 | 84.999 | 84.999 |

## 7. actual parent oracle 진단

이 표는 순수 공간배분 한계 진단이다. target children actual의 합계를 parent로 재주입하므로 운영 성능으로 사용하지 않는다.

| scenario | rows | actual_sum_eok | predicted_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells | max_ape_pct | diagnostic_only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| electricity_share_baseline_weight_1.00 | 607 | 15,501,265.286 | 15,501,265.286 | 783,916.822 | 5.057 | 163 | 44 | 120 | 208.113 | True |
| electricity_share_baseline_weight_0.75 | 607 | 15,501,265.286 | 15,501,265.286 | 1,746,633.123 | 11.268 | 333 | 154 | 267 | 696.455 | True |
| electricity_share_baseline_weight_0.50 | 607 | 15,501,265.286 | 15,501,265.286 | 3,169,980.739 | 20.450 | 430 | 288 | 356 | 1,227.058 | True |
| electricity_share_baseline_weight_0.25 | 607 | 15,501,265.286 | 15,501,265.286 | 4,664,055.307 | 30.088 | 497 | 365 | 407 | 1,822.072 | True |
| electricity_share_baseline_weight_0.00 | 607 | 15,501,265.286 | 15,501,265.286 | 6,168,015.247 | 39.790 | 535 | 431 | 437 | 2,417.087 | True |

## 8. 판정

1. 산업용 전력은 2021~2023 공개 actual 구간의 모든 광업·제조업 검증 셀에 12개월 단위로 연결된다.
2. 전체기간 discovery에서도 산업용 전력 share 단독 혼합은 기존 share보다 나아지지 않았고, 전력 비중을 높일수록 WAPE·초과오차 셀이 크게 악화됐다.
3. rolling holdout에서도 baseline 이외 후보가 훈련연도 guardrail을 통과하지 못해 baseline으로 fallback했다.
4. 공장등록은 연결률이 높아 구조 진단에는 유용하지만, 현재 snapshot/vintage 한계 때문에 2021~2023 성능 route로 쓰지 않는다.
5. 다음 승격 조건은 제조업 대형 도시를 discovery/holdout으로 분리하고, 전력·공장규모 interaction 후보를 사전 고정한 뒤 WAPE뿐 아니라 10%/20% 초과 셀과 max APE까지 비악화시키는 것이다.

## 9. 산출물

- `nationwide/outputs/phase259_mfg_electricity_candidate_detail.csv`
- `nationwide/outputs/phase259_mfg_electricity_coverage_summary.csv`
- `nationwide/outputs/phase259_mfg_factory_snapshot_diagnostic.csv`
- `nationwide/outputs/phase259_mfg_electricity_candidate_summary.csv`
- `nationwide/outputs/phase259_mfg_electricity_rolling_holdout_summary.csv`
- `nationwide/outputs/phase259_mfg_electricity_rolling_selected_detail.csv`
- `nationwide/outputs/phase259_mfg_electricity_oracle_parent_diagnostic.csv`
