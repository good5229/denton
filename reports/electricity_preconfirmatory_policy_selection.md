# 전력 Feature Pre-confirmatory Policy Selection

## 현재 상태

- champion: `global`
- challenger candidates: `R2_all_only_trainalpha_B6_rel5`, `R3b_all_only_conservative_B4_rel5`
- production replacement: prohibited
- final confirmatory challenger: `none`
- selection reason: `no_candidate_passed_all_preconfirmatory_gates`

## 후보 정의

| policy | feature bundle | alpha grid | application | fallback |
| --- | --- | --- | --- | --- |
| R2_all_only_trainalpha_B6_rel5 | B6_full_without_change | 0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.4,0.5 | all only | C00/D00/global unavailable |
| R3b_all_only_conservative_B4_rel5 | B4_level_normalized | 0.1,0.15,0.25 | all only | C00/D00/global unavailable |

## R2/R3b 성능 비교

| policy | WMAPE | global WMAPE | delta +good | relative % | macro WMAPE | median APE delta | p90 APE delta | material | +5pp | +10pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | 5.379586 | 5.470158 | 0.090573 | 1.655762 | 5.151703 | 0.05548 | 0.0 | 0 | 0 | 0 |
| R3b_all_only_conservative_B4_rel5 | 5.369693 | 5.470158 | 0.100466 | 1.836613 | 5.180697 | -0.004882 | 0.0 | 0 | 0 | 0 |

## 연도별 결과

| policy | year | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 5.849244 | 5.53633 | 0.312914 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 4.938687 | 5.159833 | -0.221146 |
| R3b_all_only_conservative_B4_rel5 | 2022 | 5.849244 | 5.621908 | 0.227336 |
| R3b_all_only_conservative_B4_rel5 | 2023 | 4.938687 | 5.016091 | -0.077404 |

## Selection-aware Bootstrap

| type | selected | count | frequency | mean | median | CI 2.5 | CI 97.5 | P(improve) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| selection_aware_delta |  |  |  | 0.093619 | 0.100197 | -0.174055 | 0.339472 | 0.746 |
| selected_policy_frequency | R2_all_only_trainalpha_B6_rel5 | 1990 | 0.995 |  |  |  |  |  |
| selected_policy_frequency | R3b_all_only_conservative_B4_rel5 | 10 | 0.005 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.4 | 1371 | 0.6855 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.5 | 290 | 0.145 |  |  |  |  |  |
| selected_alpha_frequency | 0.5/0.5 | 215 | 0.1075 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.3 | 42 | 0.021 |  |  |  |  |  |
| selected_alpha_frequency | 0.5/0.4 | 30 | 0.015 |  |  |  |  |  |
| selected_alpha_frequency | 0.3/0.4 | 23 | 0.0115 |  |  |  |  |  |
| selected_alpha_frequency | 0.25/0.25 | 10 | 0.005 |  |  |  |  |  |
| selected_alpha_frequency | 0.3/0.5 | 8 | 0.004 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.25 | 3 | 0.0015 |  |  |  |  |  |
| selected_alpha_frequency | 0.5/0.25 | 2 | 0.001 |  |  |  |  |  |
| selected_alpha_frequency | 0.15/0.5 | 1 | 0.0005 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.2 | 1 | 0.0005 |  |  |  |  |  |
| selected_alpha_frequency | 0.5/0.3 | 1 | 0.0005 |  |  |  |  |  |
| selected_alpha_frequency | 0.25/0.5 | 1 | 0.0005 |  |  |  |  |  |
| selected_alpha_frequency | 0.3/0.2 | 1 | 0.0005 |  |  |  |  |  |
| selected_alpha_frequency | 0.4/0.15 | 1 | 0.0005 |  |  |  |  |  |

## Placebo

| policy | placebo | real | mean | p90 | p95 | p99 | percentile | pass p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R2_all_only_trainalpha_B6_rel5 | region | 0.090573 | 0.061696 | 0.0763 | 0.078828 | 0.087358 | 0.994 | Y |
| R2_all_only_trainalpha_B6_rel5 | temporal | 0.090573 | 0.117034 | 0.125293 | 0.12784 | 0.13456 | 0.008 | N |
| R2_all_only_trainalpha_B6_rel5 | noise | 0.090573 | 0.082317 | 0.096681 | 0.102912 | 0.117911 | 0.804 | N |
| R3b_all_only_conservative_B4_rel5 | region | 0.100466 | 0.074228 | 0.081177 | 0.083944 | 0.090535 | 0.999 | Y |
| R3b_all_only_conservative_B4_rel5 | temporal | 0.100466 | 0.103286 | 0.104715 | 0.105109 | 0.105715 | 0.007 | N |
| R3b_all_only_conservative_B4_rel5 | noise | 0.100466 | 0.073902 | 0.081224 | 0.084389 | 0.091314 | 0.997 | Y |

## LOSO

| policy | improved | degraded | median delta | worst delta |
| --- | ---: | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | 11 | 5 | 0.071882 | -0.184183 |
| R3b_all_only_conservative_B4_rel5 | 11 | 5 | 0.096917 | -0.168469 |

## Large-observation Removal

| policy | metric | top % | global WMAPE | candidate WMAPE | delta +good |
| --- | --- | ---: | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | actual_scale | 1 | 5.628664 | 5.456571 | 0.172093 |
| R2_all_only_trainalpha_B6_rel5 | actual_scale | 5 | 5.895977 | 5.686946 | 0.209031 |
| R2_all_only_trainalpha_B6_rel5 | actual_scale | 10 | 6.246298 | 6.019661 | 0.226638 |
| R2_all_only_trainalpha_B6_rel5 | electricity_scale | 1 | 5.476955 | 5.304463 | 0.172492 |
| R2_all_only_trainalpha_B6_rel5 | electricity_scale | 5 | 5.758199 | 5.516032 | 0.242167 |
| R2_all_only_trainalpha_B6_rel5 | electricity_scale | 10 | 5.994856 | 5.749186 | 0.24567 |
| R3b_all_only_conservative_B4_rel5 | actual_scale | 1 | 5.628664 | 5.490786 | 0.137878 |
| R3b_all_only_conservative_B4_rel5 | actual_scale | 5 | 5.895977 | 5.743483 | 0.152495 |
| R3b_all_only_conservative_B4_rel5 | actual_scale | 10 | 6.246298 | 6.088574 | 0.157725 |
| R3b_all_only_conservative_B4_rel5 | electricity_scale | 1 | 5.476955 | 5.331103 | 0.145852 |
| R3b_all_only_conservative_B4_rel5 | electricity_scale | 5 | 5.758199 | 5.569526 | 0.188672 |
| R3b_all_only_conservative_B4_rel5 | electricity_scale | 10 | 5.994856 | 5.80084 | 0.194017 |

## Missingness

| policy | scenario | coverage | base delta | delta +good |
| --- | --- | ---: | ---: | ---: |
| R2_all_only_trainalpha_B6_rel5 | M1_hard_fallback_latest_month_missing |  | 0.090573 | 0.0 |
| R2_all_only_trainalpha_B6_rel5 | M2_prior_vintage_recalculation | 0.75 | 0.090573 | 0.090573 |
| R2_all_only_trainalpha_B6_rel5 | M2_prior_vintage_recalculation | 0.9 | 0.090573 | 0.090573 |
| R2_all_only_trainalpha_B6_rel5 | M2_prior_vintage_recalculation | 1.0 | 0.090573 | 0.0 |
| R3b_all_only_conservative_B4_rel5 | M1_hard_fallback_latest_month_missing |  | 0.100466 | 0.0 |
| R3b_all_only_conservative_B4_rel5 | M2_prior_vintage_recalculation | 0.75 | 0.100466 | 0.100466 |
| R3b_all_only_conservative_B4_rel5 | M2_prior_vintage_recalculation | 0.9 | 0.100466 | 0.100466 |
| R3b_all_only_conservative_B4_rel5 | M2_prior_vintage_recalculation | 1.0 | 0.100466 | -0.006215 |

## Gate 판정

| policy | gate | pass | note |
| --- | --- | --- | --- |
| R2_all_only_trainalpha_B6_rel5 | data_integrity | Y | primary vintage audit has zero leakage |
| R2_all_only_trainalpha_B6_rel5 | year_consistency | N | 2022=0.312914, 2023=-0.221146, pooled=0.090573 |
| R2_all_only_trainalpha_B6_rel5 | placebo | N | requires all three placebo p95 passes |
| R2_all_only_trainalpha_B6_rel5 | selection_aware_bootstrap | N | P(improve)=0.746 |
| R2_all_only_trainalpha_B6_rel5 | tail_stability | Y | material=0, +5pp=0, +10pp=0 |
| R2_all_only_trainalpha_B6_rel5 | region_generalization | Y | improved=11, worst=-0.184183 |
| R2_all_only_trainalpha_B6_rel5 | large_observation_removal | Y | requires positive improvement after every removal |
| R3b_all_only_conservative_B4_rel5 | data_integrity | Y | primary vintage audit has zero leakage |
| R3b_all_only_conservative_B4_rel5 | year_consistency | Y | 2022=0.227336, 2023=-0.077404, pooled=0.100466 |
| R3b_all_only_conservative_B4_rel5 | placebo | N | requires all three placebo p95 passes |
| R3b_all_only_conservative_B4_rel5 | selection_aware_bootstrap | N | P(improve)=0.746 |
| R3b_all_only_conservative_B4_rel5 | tail_stability | Y | material=0, +5pp=0, +10pp=0 |
| R3b_all_only_conservative_B4_rel5 | region_generalization | Y | improved=11, worst=-0.168469 |
| R3b_all_only_conservative_B4_rel5 | large_observation_removal | Y | requires positive improvement after every removal |

## 최종 행동양식

- confirmatory challenger: `none`
- operating policy remains: `global`
- electricity-only policy status: `closed_no_confirmatory_challenger`
- C00 policy: global fallback
- D00 policy: global fallback
- no additional 2022-2023 tuning is allowed after this report
- if challenger is `none`, electricity-only policy remains research candidate only
- unused official actual is not automatically assigned to R2/R3b confirmatory evaluation because no challenger is frozen

## 전력 Feature 최종 해석

- regional scale signal: present
- cross-sectional structure signal: present
- tail degradation: not observed
- standalone residual correction: unsupported
- stable temporal signal: insufficient
- future use: auxiliary or interaction variable with factory, industrial complex, building, business, or employment sources

## 종료 규칙

- same-actual retuning allowed: `false`
- 2022-2023 actual role: development actual only
- R2/R3b production use: prohibited
- R2/R3b confirmatory use: prohibited
- future ML restart requires at least one non-electricity structural source to be ML-ready, preregistration committed, candidate bundles frozen, and acceptance gates frozen

## Manifest 요약

- manifest: `data/processed/electricity_confirmatory_challenger_manifest.json`
- manifest challenger: `null` when `confirmatory_challenger` is `none`
- confirmatory actual: 2024 이후 또는 최초 미사용 official actual
- confirmatory failure action: reject frozen challenger and retain global; no same-actual retuning
