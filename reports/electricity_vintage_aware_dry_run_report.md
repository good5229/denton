# 전력 Feature Vintage-aware Dry-run 결과

## 실행 요약

KEPCO 과거 source vintage를 prediction-origin 기준 as-of feature로 변환하고, 시군구 official actual pilot과 결합해 dry-run ablation을 수행했다. 모델은 `numpy` 기반 Ridge residual correction이며 temporal split은 `Train 2021 -> Test 2022`, `Train 2021-2022 -> Test 2023`으로 고정했다.

- panel rows: 7,092
- decision: `guardrailed_candidate_needs_robustness`
- headline interpretation: 전력 보정을 full strength로 적용한 M3는 악화됐지만, 보정량을 0.25로 제한한 M4는 WMAPE를 개선했다. 따라서 운영 채택이 아니라 guardrail 후보로 남기고 강건성 검증을 이어간다.

## Main Policy Comparison

| policy | count | wmape | macro_region_wmape | median_ape | p90_ape | material_degradation_count | improvement_vs_global_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M0_baseline | 4404 | 5.425156 | 5.289317 | 5.982753 | 30.252651 | 212 | 0.822682 |
| M1_global | 4404 | 5.470158 | 5.343632 | 5.897335 | 30.216904 | 0 | 0.0 |
| M2B_baseline_electricity | 4404 | 6.138002 | 5.734634 | 7.701742 | 30.93249 | 2079 | -12.208861 |
| M3_global_electricity | 4404 | 5.938832 | 5.648843 | 7.556686 | 30.243343 | 1987 | -8.567833 |
| M4_global_electricity_alpha_0.25 | 4404 | 5.363593 | 5.215353 | 6.239512 | 30.281074 | 500 | 1.948116 |
| M4_global_electricity_alpha_0.5 | 4404 | 5.425765 | 5.241069 | 6.5025 | 30.67632 | 1258 | 0.811549 |
| M4_global_electricity_alpha_0.75 | 4404 | 5.625721 | 5.391708 | 6.895973 | 30.4341 | 1733 | -2.843848 |

## Year Comparison

| policy | target_year | count | wmape | improvement_vs_global_pct |
| --- | ---: | ---: | ---: | ---: |
| M0_baseline | 2022 | 2684 | 5.823494 | 0.440229 |
| M0_baseline | 2023 | 1720 | 4.866693 | 1.457764 |
| M1_global | 2022 | 2684 | 5.849244 | 1e-06 |
| M1_global | 2023 | 1720 | 4.938687 | 8e-06 |
| M2B_baseline_electricity | 2022 | 2684 | 5.921174 | -1.22973 |
| M2B_baseline_electricity | 2023 | 1720 | 6.44199 | -30.439315 |
| M3_global_electricity | 2022 | 2684 | 5.812888 | 0.621552 |
| M3_global_electricity | 2023 | 1720 | 6.115403 | -23.826485 |
| M4_global_electricity_alpha_0.25 | 2022 | 2684 | 5.681298 | 2.871244 |
| M4_global_electricity_alpha_0.25 | 2023 | 1720 | 4.918177 | 0.4153 |
| M4_global_electricity_alpha_0.5 | 2022 | 2684 | 5.625796 | 3.820119 |
| M4_global_electricity_alpha_0.5 | 2023 | 1720 | 5.145326 | -4.18408 |
| M4_global_electricity_alpha_0.75 | 2022 | 2684 | 5.676082 | 2.960418 |
| M4_global_electricity_alpha_0.75 | 2023 | 1720 | 5.555116 | -12.481629 |

## Industry Comparison

| policy | industry | count | wmape | p90_ape | improvement_vs_global_pct |
| --- | --- | ---: | ---: | ---: | ---: |
| M0_baseline | C00 | 1504 | 5.774172 | 14.949912 | 0.747504 |
| M0_baseline | D00 | 1396 | 18.210087 | 76.636773 | 1.87901 |
| M0_baseline | all | 1504 | 4.957608 | 11.930548 | 0.761941 |
| M1_global | C00 | 1504 | 5.817659 | 14.958939 | 4e-06 |
| M1_global | D00 | 1396 | 18.558809 | 72.235901 | -0.0 |
| M1_global | all | 1504 | 4.995672 | 11.661827 | 1e-06 |
| M2B_baseline_electricity | C00 | 1504 | 7.145227 | 18.474267 | -22.81962 |
| M2B_baseline_electricity | D00 | 1396 | 18.418291 | 75.438051 | 0.757149 |
| M2B_baseline_electricity | all | 1504 | 5.403246 | 11.49928 | -8.158541 |
| M3_global_electricity | C00 | 1504 | 6.464948 | 19.511213 | -11.126275 |
| M3_global_electricity | D00 | 1396 | 19.556319 | 67.828723 | -5.37486 |
| M3_global_electricity | all | 1504 | 5.375213 | 11.445111 | -7.597395 |
| M4_global_electricity_alpha_0.25 | C00 | 1504 | 5.699718 | 14.746232 | 2.027297 |
| M4_global_electricity_alpha_0.25 | D00 | 1396 | 18.744336 | 70.306028 | -0.999671 |
| M4_global_electricity_alpha_0.25 | all | 1504 | 4.886651 | 11.564153 | 2.18231 |
| M4_global_electricity_alpha_0.5 | C00 | 1504 | 5.827362 | 15.408901 | -0.166781 |
| M4_global_electricity_alpha_0.5 | D00 | 1396 | 18.978422 | 68.699779 | -2.260991 |
| M4_global_electricity_alpha_0.5 | all | 1504 | 4.916698 | 11.196527 | 1.58085 |
| M4_global_electricity_alpha_0.75 | C00 | 1504 | 6.071532 | 17.1453 | -4.36383 |
| M4_global_electricity_alpha_0.75 | D00 | 1396 | 19.247368 | 67.843538 | -3.710147 |
| M4_global_electricity_alpha_0.75 | all | 1504 | 5.096137 | 11.001479 | -2.011039 |

## Origin Comparison

| policy | origin | latest_eligible_month | feature_coverage | wmape |
| --- | --- | --- | ---: | ---: |
| M0_baseline | O0 | 202209 | 0.949213 | 5.425156 |
| M0_baseline | O1 | 202212 | 1.0 | 5.425156 |
| M0_baseline | O2 | 202303 | 1.0 | 5.425156 |
| M0_baseline | O3 | 202307 | 1.0 | 5.425156 |
| M1_global | O0 | 202209 | 0.949213 | 5.470158 |
| M1_global | O1 | 202212 | 1.0 | 5.470158 |
| M1_global | O2 | 202303 | 1.0 | 5.470158 |
| M1_global | O3 | 202307 | 1.0 | 5.470158 |
| M2B_baseline_electricity | O0 | 202209 | 0.949213 | 6.439409 |
| M2B_baseline_electricity | O1 | 202212 | 1.0 | 6.170754 |
| M2B_baseline_electricity | O2 | 202303 | 1.0 | 6.001147 |
| M2B_baseline_electricity | O3 | 202307 | 1.0 | 5.940696 |
| M3_global_electricity | O0 | 202209 | 0.949213 | 5.997675 |
| M3_global_electricity | O1 | 202212 | 1.0 | 6.205429 |
| M3_global_electricity | O2 | 202303 | 1.0 | 5.641972 |
| M3_global_electricity | O3 | 202307 | 1.0 | 5.910252 |
| M4_global_electricity_alpha_0.25 | O0 | 202209 | 0.949213 | 5.400309 |
| M4_global_electricity_alpha_0.25 | O1 | 202212 | 1.0 | 5.322194 |
| M4_global_electricity_alpha_0.25 | O2 | 202303 | 1.0 | 5.361405 |
| M4_global_electricity_alpha_0.25 | O3 | 202307 | 1.0 | 5.370464 |
| M4_global_electricity_alpha_0.5 | O0 | 202209 | 0.949213 | 5.466654 |
| M4_global_electricity_alpha_0.5 | O1 | 202212 | 1.0 | 5.477868 |
| M4_global_electricity_alpha_0.5 | O2 | 202303 | 1.0 | 5.3511 |
| M4_global_electricity_alpha_0.5 | O3 | 202307 | 1.0 | 5.407438 |
| M4_global_electricity_alpha_0.75 | O0 | 202209 | 0.949213 | 5.671311 |
| M4_global_electricity_alpha_0.75 | O1 | 202212 | 1.0 | 5.781827 |
| M4_global_electricity_alpha_0.75 | O2 | 202303 | 1.0 | 5.444734 |
| M4_global_electricity_alpha_0.75 | O3 | 202307 | 1.0 | 5.605013 |

## Placebo Comparison

| experiment | wmape | improvement_vs_global_pct | interpretation |
| --- | ---: | ---: | --- |
| region_permutation | 6.904764 | -26.22604 | diagnostic_only |
| random_noise | 7.074431 | -29.327732 | diagnostic_only |
| latest_source_leakage_benchmark | 6.205452 | -13.441916 | leakage_upper_bound_only |

## Feature Ablation

| feature_bundle | wmape | p90_ape | material_degradation_count |
| --- | ---: | ---: | ---: |
| A1_level_only | 6.124549 | 30.584664 | 2202 |
| A3_composition_only | 6.117716 | 30.085033 | 2143 |
| A4_change_only | 7.128466 | 30.454365 | 2267 |
| A5_level_normalized | 5.849908 | 30.587169 | 2134 |
| A6_full_minimal | 5.938832 | 30.243343 | 1987 |

## 방법론 메모

- Primary model은 dependency/runtime drift를 피하기 위해 `numpy`로 직접 구현한 Ridge residual correction이다.
- 현재 official pilot에는 `E00`이 없어 1차 dry-run에서는 `C00`, `D00`, `all`만 평가했다.
- 현재 KEPCO parser는 kWh sheet만 노출하므로 고객호수 기반 intensity feature는 제외했다.
- 이번 headline table은 prediction origin별 예측 과업을 모두 포함한다. 따라서 baseline/global도 origin별로 반복 평가된다.
- Bootstrap, future-lead placebo, missingness simulation, leave-one-sido-out은 다음 robustness round로 남겼다.
