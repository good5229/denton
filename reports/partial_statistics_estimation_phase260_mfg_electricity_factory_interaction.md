# Phase260 광업·제조업 전력×공장구조 interaction holdout

생성시각: 2026-07-29T20:58:32+09:00

## 1. 목적

Phase259에서 산업용 전력 share 단독혼합은 baseline을 이기지 못했다. 이번 실험은 전력에 공장규모·업종구성 moderator를 결합한 사전정의 interaction 후보가 rolling holdout에서 기준선을 넘는지 점검한다. 공장등록은 current snapshot이므로 strict nowcast route가 아니라 retrospective diagnostic/refinement 후보로만 사용한다.

## 2. 사전정의 설계

| 항목 | 설정 |
| --- | --- |
| 대상 | `광업, 제조업` 시군구×연간 GVA, 2021~2023 |
| primary parent total | 기존 baseline의 시도×연도 예측 합계 유지 |
| 금지 | target actual parent 재주입, city-specific boost, sparse 대표업종 직접학습 |
| factory 사용 | 2021~2023 공통 정적 구조 moderator. 연도별 공장 stock 변화로 해석 금지 |
| KSIC bucket | 소재형, 기계·전기·전자·운송장비형, 소비재·경공업형, 기타, 미해결 |
| 후보 | 공장 종업원 share, 제조시설면적 share, 전력×대기업비중, 전력×소재형, 전력×기계·전자·운송장비형, 전력×업종집중도, 공장 종업원×면적, 전력×종업원×면적 |
| baseline weight | `0.95, 0.90, 0.75` |
| rolling 선택 | 2021→2022, 2021~2022→2023. 훈련연도에서 WAPE·10%·20%·대형 actual 10%·max APE 모두 비악화일 때만 선택 |

## 3. coverage

| year | validation_cells | electricity_full12_cells | electricity_leakage_ok12_cells | cells_with_factory | actual_sum_eok | baseline_predicted_sum_eok |
| --- | --- | --- | --- | --- | --- | --- |
| 2021 | 229 | 229 | 229 | 229 | 5,658,407.51 | 5,658,407.45 |
| 2022 | 229 | 229 | 229 | 229 | 5,807,028.88 | 5,795,412.54 |
| 2023 | 149 | 149 | 149 | 149 | 4,035,828.90 | 4,066,324.13 |

## 4. 공장구조 feature 요약

| year | employee_sum | mfg_area_sum | avg_large_employee_ratio | avg_materials_share | avg_machinery_share | avg_top_bucket_share |
| --- | --- | --- | --- | --- | --- | --- |
| 2021 | 3,736,055 | 278,543,378.271 | 0.123 | 0.266 | 0.336 | 0.550 |
| 2022 | 3,736,055 | 278,543,378.271 | 0.123 | 0.266 | 0.336 | 0.550 |
| 2023 | 2,504,424 | 175,461,515.893 | 0.120 | 0.259 | 0.331 | 0.549 |

## 5. 전체기간 후보 성능 탐색표

이 표는 discovery용이며 route 채택 근거가 아니다.

| scenario | rows | actual_sum_eok | predicted_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells | max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 607 | 15,501,265.286 | 15,520,144.122 | 882,479.816 | 5.693 | 172 | 45 | 122 | 212.492 |
| electricity_x_machinery_transport_electronics_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 915,155.067 | 5.904 | 202 | 68 | 141 | 301.852 |
| electricity_x_large_factory_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 916,492.631 | 5.912 | 201 | 68 | 141 | 295.993 |
| electricity_x_top_bucket_concentration_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 918,338.234 | 5.924 | 204 | 69 | 143 | 310.611 |
| electricity_x_materials_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 925,385.021 | 5.970 | 205 | 69 | 144 | 316.181 |
| electricity_factory_emp_area_geomean_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 971,710.891 | 6.269 | 223 | 66 | 157 | 224.180 |
| factory_employee_share_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 1,006,326.360 | 6.492 | 230 | 79 | 161 | 208.129 |
| factory_emp_area_geomean_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 1,019,428.806 | 6.576 | 232 | 77 | 163 | 208.655 |
| electricity_x_machinery_transport_electronics_baseline_weight_0.90 | 607 | 15,501,265.286 | 15,520,144.122 | 1,036,211.644 | 6.685 | 239 | 87 | 172 | 391.212 |
| electricity_x_top_bucket_concentration_baseline_weight_0.90 | 607 | 15,501,265.286 | 15,520,144.122 | 1,042,464.930 | 6.725 | 243 | 90 | 169 | 408.731 |
| factory_area_share_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,520,144.122 | 1,045,347.459 | 6.744 | 226 | 73 | 164 | 209.126 |
| electricity_x_large_factory_baseline_weight_0.90 | 607 | 15,501,265.286 | 15,520,144.122 | 1,045,399.464 | 6.744 | 233 | 88 | 169 | 379.495 |

## 6. rolling holdout 결과

| holdout_year | train_years | selected_scenario | selection_reason | baseline_wape_pct | selected_wape_pct | wape_delta_pp | baseline_over10_cells | selected_over10_cells | baseline_over20_cells | selected_over20_cells | baseline_large_actual_over10_cells | selected_large_actual_over10_cells | baseline_max_ape_pct | selected_max_ape_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 2021 | baseline | fallback_no_nonbaseline_train_safe_candidate | 5.535 | 5.535 | 0.000 | 50 | 50 | 10 | 10 | 37 | 37 | 44.751 | 44.751 |
| 2023 | 2021,2022 | baseline | fallback_no_nonbaseline_train_safe_candidate | 5.467 | 5.467 | 0.000 | 47 | 47 | 13 | 13 | 36 | 36 | 84.999 | 84.999 |

## 7. actual parent oracle 진단

운영 성능이 아니라 순수 공간배분 한계 진단이다.

| scenario | rows | actual_sum_eok | predicted_sum_eok | abs_error_sum_eok | wape_pct | over10_cells | over20_cells | large_actual_over10_cells | max_ape_pct | diagnostic_only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 607 | 15,501,265.286 | 15,501,265.286 | 783,916.822 | 5.057 | 163 | 44 | 120 | 208.113 | True |
| electricity_x_machinery_transport_electronics_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 831,974.814 | 5.367 | 179 | 66 | 130 | 296.221 | True |
| electricity_x_large_factory_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 832,498.059 | 5.371 | 181 | 66 | 132 | 290.444 | True |
| electricity_x_top_bucket_concentration_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 836,525.065 | 5.396 | 188 | 68 | 136 | 304.857 | True |
| electricity_x_materials_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 843,209.419 | 5.440 | 186 | 68 | 136 | 310.348 | True |
| electricity_factory_emp_area_geomean_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 880,305.216 | 5.679 | 209 | 63 | 148 | 219.637 | True |
| factory_employee_share_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 919,898.726 | 5.934 | 225 | 75 | 160 | 203.811 | True |
| factory_emp_area_geomean_baseline_weight_0.95 | 607 | 15,501,265.286 | 15,501,265.286 | 927,395.451 | 5.983 | 216 | 76 | 158 | 204.329 | True |

## 8. 판정

1. 전력×공장구조 interaction은 전력 단독보다 훨씬 보수적인 후보지만, 공장등록 snapshot 한계 때문에 운영 route로 채택하지 않는다.
2. rolling holdout에서 baseline 이외 후보가 guardrail을 통과하지 못하면 baseline으로 fallback한다.
3. 만약 특정 후보가 훈련 gate를 통과하더라도 2023 coverage가 11개 시도/149셀로 축소되어 있으므로, 추가 외부연도 또는 city holdout 확인 전에는 채택하지 않는다.
4. 다음 자료 개선 우선순위는 공장등록 vintage/폐업·변경이력, 제조업 중분류 금액형 구조자료, 대형사업장/산단 단위 생산·출하·투자 자료다.

## 9. 산출물

- `nationwide/outputs/phase260_mfg_interaction_feature_frame.csv`
- `nationwide/outputs/phase260_mfg_interaction_coverage_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_factory_feature_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_candidate_detail.csv`
- `nationwide/outputs/phase260_mfg_interaction_candidate_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_rolling_holdout_summary.csv`
- `nationwide/outputs/phase260_mfg_interaction_rolling_selected_detail.csv`
- `nationwide/outputs/phase260_mfg_interaction_oracle_parent_diagnostic.csv`
