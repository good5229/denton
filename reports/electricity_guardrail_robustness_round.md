# 전력 Feature Guardrail Robustness Round

## 1. 결론

- final decision: `guardrailed_candidate_needs_refinement`
- primary origin: `O1`
- best candidate: `P4_trainalpha_B6_relative_rel5_S1`
- global WMAPE: 5.470158
- best candidate WMAPE: 5.15084
- WMAPE delta, positive is good: 0.319318
- pooled bootstrap improvement probability: 0.999
- primary material degradation count: 137

이번 라운드는 `alpha=0.25`를 운영 정책으로 바로 채택하지 않고, O1 기준에서 후보 정책을 여러 stress test로 흔들어 본 검증이다. 훈련/검증/테스트의 시간 순서를 지켜 2023년 예측에는 2023년 이후 공개 정보를 쓰지 않았다.

## 2. 데이터와 Vintage Guardrail

- feature source: KEPCO 시군구 전력 사용량 historical source vintage
- target: 시군구 official actual pilot의 `C00`, `D00`, `all`
- O1 definition: 예측연도 3월 말 기준 공표 완료 데이터만 사용
- fallback: feature 미사용 산업 또는 결측 stress에서는 global reference 유지

## 3. 정책 후보 비교

| policy | count | WMAPE | macro WMAPE | median APE | p90 APE | global WMAPE same rows | delta +good | material degradation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P0_global_reference | 1101 | 5.470158 | 5.343632 | 5.897335 | 30.216904 |  |  | 0 |
| P1_fixed025_B4_relative_rel5_S1 | 1101 | 5.347381 | 5.141416 | 5.844294 | 30.216904 | 5.470158 | 0.122777 | 0 |
| P2_trainalpha_B4_relative_rel5_S1 | 1101 | 5.333 | 5.059878 | 5.79384 | 30.216904 | 5.470158 | 0.137158 | 181 |
| P3_fixed025_B4_absolute_q95_S1 | 1101 | 5.505642 | 5.383931 | 6.810076 | 36.75698 | 5.470158 | -0.035484 | 181 |
| P4_trainalpha_B6_relative_rel5_S1 | 1101 | 5.15084 | 4.936479 | 5.689861 | 30.216904 | 5.470158 | 0.319318 | 137 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | 1101 | 5.489568 | 5.397658 | 5.993558 | 30.216904 | 5.470158 | -0.01941 | 91 |
| P6_trainalpha_B4_relative_rel5_S3_all | 1101 | 5.328811 | 5.091978 | 5.814276 | 30.216904 | 5.470158 | 0.141347 | 30 |
| bundle_B1_level_only | 1101 | 5.298386 | 5.036039 | 5.794011 | 30.216904 | 5.470158 | 0.171772 | 173 |
| bundle_B3_composition_only | 1101 | 5.372137 | 5.085613 | 5.902532 | 30.216904 | 5.470158 | 0.098021 | 186 |
| bundle_B4_level_normalized | 1101 | 5.333 | 5.059878 | 5.79384 | 30.216904 | 5.470158 | 0.137158 | 181 |
| bundle_B5_full_minimal | 1101 | 5.160992 | 4.938605 | 5.729714 | 30.216904 | 5.470158 | 0.309166 | 132 |
| bundle_B6_full_without_change | 1101 | 5.15084 | 4.936479 | 5.689861 | 30.216904 | 5.470158 | 0.319318 | 137 |
| bundle_B7_normalized_only | 1101 | 5.372137 | 5.085613 | 5.902532 | 30.216904 | 5.470158 | 0.098021 | 186 |
| bundle_B8_change_only_negative_control | 1101 | 5.617738 | 5.235431 | 5.759433 | 30.216904 | 5.470158 | -0.14758 | 161 |
| clip_q90 | 1101 | 5.315132 | 4.9908 | 5.786677 | 30.216904 | 5.470158 | 0.155026 | 190 |
| clip_q95 | 1101 | 5.329381 | 5.007589 | 5.777509 | 30.216904 | 5.470158 | 0.140777 | 192 |
| clip_q99 | 1101 | 5.320285 | 5.000308 | 5.777509 | 30.216904 | 5.470158 | 0.149873 | 194 |
| clip_rel0.02 | 1101 | 5.446336 | 5.227642 | 5.898481 | 30.216904 | 5.470158 | 0.023822 | 0 |
| clip_rel0.05 | 1101 | 5.333 | 5.059878 | 5.79384 | 30.216904 | 5.470158 | 0.137158 | 181 |
| clip_rel0.10 | 1101 | 5.300839 | 4.98758 | 5.777509 | 30.216904 | 5.470158 | 0.169319 | 194 |
| mask_S0_all_apply | 1101 | 5.336176 | 5.298566 | 5.972912 | 30.685074 | 5.470158 | 0.133982 | 2 |
| mask_S1_C00_all_apply_D00_fallback | 1101 | 5.333 | 5.059878 | 5.79384 | 30.216904 | 5.470158 | 0.137158 | 181 |
| mask_S2_C00_only | 1101 | 5.489568 | 5.397658 | 5.993558 | 30.216904 | 5.470158 | -0.01941 | 91 |
| mask_S3_all_only | 1101 | 5.328811 | 5.091978 | 5.814276 | 30.216904 | 5.470158 | 0.141347 | 30 |
| target_absolute | 1101 | 5.410676 | 5.201776 | 5.966564 | 29.847681 | 5.470158 | 0.059482 | 187 |
| target_log_ratio | 1101 | 5.358411 | 5.091508 | 5.852978 | 30.216904 | 5.470158 | 0.111747 | 214 |
| target_relative | 1101 | 5.333 | 5.059878 | 5.79384 | 30.216904 | 5.470158 | 0.137158 | 181 |

## 4. 연도/산업/지역별 진단

| grouping | policy | key | count | WMAPE | global WMAPE | delta +good |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| target_year | P1_fixed025_B4_relative_rel5_S1 | 2022 | 671 | 5.572387 | 5.849244 | 0.276857 |
| target_year | P1_fixed025_B4_relative_rel5_S1 | 2023 | 430 | 5.031925 | 4.938687 | -0.093238 |
| target_year | P2_trainalpha_B4_relative_rel5_S1 | 2022 | 671 | 5.435939 | 5.849244 | 0.413305 |
| target_year | P2_trainalpha_B4_relative_rel5_S1 | 2023 | 430 | 5.188682 | 4.938687 | -0.249995 |
| target_year | P3_fixed025_B4_absolute_q95_S1 | 2022 | 671 | 5.779967 | 5.849244 | 0.069277 |
| target_year | P3_fixed025_B4_absolute_q95_S1 | 2023 | 430 | 5.121044 | 4.938687 | -0.182357 |
| target_year | P4_trainalpha_B6_relative_rel5_S1 | 2022 | 671 | 5.426617 | 5.849244 | 0.422627 |
| target_year | P4_trainalpha_B6_relative_rel5_S1 | 2023 | 430 | 4.764205 | 4.938687 | 0.174482 |
| target_year | P5_trainalpha_B4_relative_rel5_S2_C00 | 2022 | 671 | 5.870235 | 5.849244 | -0.020991 |
| target_year | P5_trainalpha_B4_relative_rel5_S2_C00 | 2023 | 430 | 4.95588 | 4.938687 | -0.017193 |
| target_year | P6_trainalpha_B4_relative_rel5_S3_all | 2022 | 671 | 5.431686 | 5.849244 | 0.417558 |
| target_year | P6_trainalpha_B4_relative_rel5_S3_all | 2023 | 430 | 5.184582 | 4.938687 | -0.245895 |
| target_year | bundle_B1_level_only | 2022 | 671 | 5.405898 | 5.849244 | 0.443346 |
| target_year | bundle_B1_level_only | 2023 | 430 | 5.147658 | 4.938687 | -0.208971 |
| target_year | bundle_B3_composition_only | 2022 | 671 | 5.395954 | 5.849244 | 0.45329 |
| target_year | bundle_B3_composition_only | 2023 | 430 | 5.338746 | 4.938687 | -0.400059 |
| target_year | bundle_B4_level_normalized | 2022 | 671 | 5.435939 | 5.849244 | 0.413305 |
| target_year | bundle_B4_level_normalized | 2023 | 430 | 5.188682 | 4.938687 | -0.249995 |
| target_year | bundle_B5_full_minimal | 2022 | 671 | 5.436048 | 5.849244 | 0.413196 |
| target_year | bundle_B5_full_minimal | 2023 | 430 | 4.775368 | 4.938687 | 0.163319 |
| target_year | bundle_B6_full_without_change | 2022 | 671 | 5.426617 | 5.849244 | 0.422627 |
| target_year | bundle_B6_full_without_change | 2023 | 430 | 4.764205 | 4.938687 | 0.174482 |
| target_year | bundle_B7_normalized_only | 2022 | 671 | 5.395954 | 5.849244 | 0.45329 |
| target_year | bundle_B7_normalized_only | 2023 | 430 | 5.338746 | 4.938687 | -0.400059 |
| target_year | bundle_B8_change_only_negative_control | 2022 | 671 | 5.692164 | 5.849244 | 0.15708 |
| target_year | bundle_B8_change_only_negative_control | 2023 | 430 | 5.513395 | 4.938687 | -0.574708 |
| target_year | clip_q90 | 2022 | 671 | 5.411732 | 5.849244 | 0.437512 |
| target_year | clip_q90 | 2023 | 430 | 5.1797 | 4.938687 | -0.241013 |
| target_year | clip_q95 | 2022 | 671 | 5.423913 | 5.849244 | 0.425331 |
| target_year | clip_q95 | 2023 | 430 | 5.196849 | 4.938687 | -0.258162 |
| target_year | clip_q99 | 2022 | 671 | 5.391163 | 5.849244 | 0.458081 |
| target_year | clip_q99 | 2023 | 430 | 5.220916 | 4.938687 | -0.282229 |
| target_year | clip_rel0.02 | 2022 | 671 | 5.674917 | 5.849244 | 0.174327 |
| target_year | clip_rel0.02 | 2023 | 430 | 5.125869 | 4.938687 | -0.187182 |
| target_year | clip_rel0.05 | 2022 | 671 | 5.435939 | 5.849244 | 0.413305 |
| target_year | clip_rel0.05 | 2023 | 430 | 5.188682 | 4.938687 | -0.249995 |
| target_year | clip_rel0.10 | 2022 | 671 | 5.380696 | 5.849244 | 0.468548 |
| target_year | clip_rel0.10 | 2023 | 430 | 5.188881 | 4.938687 | -0.250194 |
| target_year | mask_S0_all_apply | 2022 | 671 | 5.849244 | 5.849244 | 0.0 |
| target_year | mask_S0_all_apply | 2023 | 430 | 4.616864 | 4.938687 | 0.321823 |
| target_year | mask_S1_C00_all_apply_D00_fallback | 2022 | 671 | 5.435939 | 5.849244 | 0.413305 |
| target_year | mask_S1_C00_all_apply_D00_fallback | 2023 | 430 | 5.188682 | 4.938687 | -0.249995 |
| target_year | mask_S2_C00_only | 2022 | 671 | 5.870235 | 5.849244 | -0.020991 |
| target_year | mask_S2_C00_only | 2023 | 430 | 4.95588 | 4.938687 | -0.017193 |
| target_year | mask_S3_all_only | 2022 | 671 | 5.431686 | 5.849244 | 0.417558 |
| target_year | mask_S3_all_only | 2023 | 430 | 5.184582 | 4.938687 | -0.245895 |
| target_year | target_absolute | 2022 | 671 | 5.593791 | 5.849244 | 0.255453 |
| target_year | target_absolute | 2023 | 430 | 5.153953 | 4.938687 | -0.215266 |
| target_year | target_log_ratio | 2022 | 671 | 5.445586 | 5.849244 | 0.403658 |
| target_year | target_log_ratio | 2023 | 430 | 5.236194 | 4.938687 | -0.297507 |
| target_year | target_relative | 2022 | 671 | 5.435939 | 5.849244 | 0.413305 |
| target_year | target_relative | 2023 | 430 | 5.188682 | 4.938687 | -0.249995 |
| sector_code | P1_fixed025_B4_relative_rel5_S1 | C00 | 376 | 6.032724 | 5.817659 | -0.215065 |
| sector_code | P1_fixed025_B4_relative_rel5_S1 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P1_fixed025_B4_relative_rel5_S1 | all | 376 | 4.726212 | 4.995672 | 0.26946 |
| sector_code | P2_trainalpha_B4_relative_rel5_S1 | C00 | 376 | 6.317993 | 5.817659 | -0.500334 |
| sector_code | P2_trainalpha_B4_relative_rel5_S1 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P2_trainalpha_B4_relative_rel5_S1 | all | 376 | 4.58409 | 4.995672 | 0.411582 |
| sector_code | P3_fixed025_B4_absolute_q95_S1 | C00 | 376 | 6.296482 | 5.817659 | -0.478823 |
| sector_code | P3_fixed025_B4_absolute_q95_S1 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P3_fixed025_B4_absolute_q95_S1 | all | 376 | 4.843578 | 4.995672 | 0.152094 |
| sector_code | P4_trainalpha_B6_relative_rel5_S1 | C00 | 376 | 6.059613 | 5.817659 | -0.241954 |
| sector_code | P4_trainalpha_B6_relative_rel5_S1 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P4_trainalpha_B6_relative_rel5_S1 | all | 376 | 4.429783 | 4.995672 | 0.565889 |
| sector_code | P5_trainalpha_B4_relative_rel5_S2_C00 | C00 | 376 | 5.883868 | 5.817659 | -0.066209 |
| sector_code | P5_trainalpha_B4_relative_rel5_S2_C00 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P5_trainalpha_B4_relative_rel5_S2_C00 | all | 376 | 4.995672 | 4.995672 | 0.0 |
| sector_code | P6_trainalpha_B4_relative_rel5_S3_all | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | P6_trainalpha_B4_relative_rel5_S3_all | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | P6_trainalpha_B4_relative_rel5_S3_all | all | 376 | 4.790709 | 4.995672 | 0.204963 |
| sector_code | bundle_B1_level_only | C00 | 376 | 6.238288 | 5.817659 | -0.420629 |
| sector_code | bundle_B1_level_only | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B1_level_only | all | 376 | 4.567781 | 4.995672 | 0.427891 |
| sector_code | bundle_B3_composition_only | C00 | 376 | 6.350103 | 5.817659 | -0.532444 |
| sector_code | bundle_B3_composition_only | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B3_composition_only | all | 376 | 4.627192 | 4.995672 | 0.36848 |
| sector_code | bundle_B4_level_normalized | C00 | 376 | 6.317993 | 5.817659 | -0.500334 |
| sector_code | bundle_B4_level_normalized | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B4_level_normalized | all | 376 | 4.58409 | 4.995672 | 0.411582 |
| sector_code | bundle_B5_full_minimal | C00 | 376 | 6.069848 | 5.817659 | -0.252189 |
| sector_code | bundle_B5_full_minimal | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B5_full_minimal | all | 376 | 4.440154 | 4.995672 | 0.555518 |
| sector_code | bundle_B6_full_without_change | C00 | 376 | 6.059613 | 5.817659 | -0.241954 |
| sector_code | bundle_B6_full_without_change | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B6_full_without_change | all | 376 | 4.429783 | 4.995672 | 0.565889 |
| sector_code | bundle_B7_normalized_only | C00 | 376 | 6.350103 | 5.817659 | -0.532444 |
| sector_code | bundle_B7_normalized_only | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B7_normalized_only | all | 376 | 4.627192 | 4.995672 | 0.36848 |
| sector_code | bundle_B8_change_only_negative_control | C00 | 376 | 6.710834 | 5.817659 | -0.893175 |
| sector_code | bundle_B8_change_only_negative_control | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | bundle_B8_change_only_negative_control | all | 376 | 4.829982 | 4.995672 | 0.16569 |
| sector_code | clip_q90 | C00 | 376 | 6.229566 | 5.817659 | -0.411907 |
| sector_code | clip_q90 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_q90 | all | 376 | 4.595771 | 4.995672 | 0.399901 |
| sector_code | clip_q95 | C00 | 376 | 6.2782 | 5.817659 | -0.460541 |
| sector_code | clip_q95 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_q95 | all | 376 | 4.595759 | 4.995672 | 0.399913 |
| sector_code | clip_q99 | C00 | 376 | 6.316647 | 5.817659 | -0.498988 |
| sector_code | clip_q99 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_q99 | all | 376 | 4.566226 | 4.995672 | 0.429446 |
| sector_code | clip_rel0.02 | C00 | 376 | 6.127242 | 5.817659 | -0.309583 |
| sector_code | clip_rel0.02 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_rel0.02 | all | 376 | 4.829524 | 4.995672 | 0.166148 |
| sector_code | clip_rel0.05 | C00 | 376 | 6.317993 | 5.817659 | -0.500334 |
| sector_code | clip_rel0.05 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_rel0.05 | all | 376 | 4.58409 | 4.995672 | 0.411582 |
| sector_code | clip_rel0.10 | C00 | 376 | 6.338776 | 5.817659 | -0.521117 |
| sector_code | clip_rel0.10 | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | clip_rel0.10 | all | 376 | 4.52862 | 4.995672 | 0.467052 |
| sector_code | mask_S0_all_apply | C00 | 376 | 5.643252 | 5.817659 | 0.174407 |
| sector_code | mask_S0_all_apply | D00 | 349 | 18.633732 | 18.558809 | -0.074923 |
| sector_code | mask_S0_all_apply | all | 376 | 4.873659 | 4.995672 | 0.122013 |
| sector_code | mask_S1_C00_all_apply_D00_fallback | C00 | 376 | 6.317993 | 5.817659 | -0.500334 |
| sector_code | mask_S1_C00_all_apply_D00_fallback | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | mask_S1_C00_all_apply_D00_fallback | all | 376 | 4.58409 | 4.995672 | 0.411582 |
| sector_code | mask_S2_C00_only | C00 | 376 | 5.883868 | 5.817659 | -0.066209 |
| sector_code | mask_S2_C00_only | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | mask_S2_C00_only | all | 376 | 4.995672 | 4.995672 | 0.0 |
| sector_code | mask_S3_all_only | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | mask_S3_all_only | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | mask_S3_all_only | all | 376 | 4.790709 | 4.995672 | 0.204963 |
| sector_code | target_absolute | C00 | 376 | 6.195849 | 5.817659 | -0.37819 |
| sector_code | target_absolute | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | target_absolute | all | 376 | 4.74865 | 4.995672 | 0.247022 |
| sector_code | target_log_ratio | C00 | 376 | 6.35856 | 5.817659 | -0.540901 |
| sector_code | target_log_ratio | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | target_log_ratio | all | 376 | 4.603694 | 4.995672 | 0.391978 |
| sector_code | target_relative | C00 | 376 | 6.317993 | 5.817659 | -0.500334 |
| sector_code | target_relative | D00 | 349 | 18.558809 | 18.558809 | -0.0 |
| sector_code | target_relative | all | 376 | 4.58409 | 4.995672 | 0.411582 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 강원특별자치도 | 54 | 5.808936 | 6.731901 | 0.922965 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 경기도 | 164 | 5.472129 | 5.581454 | 0.109325 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 경상남도 | 54 | 2.435872 | 2.829606 | 0.393734 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 경상북도 | 138 | 5.122882 | 5.025512 | -0.09737 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 광주광역시 | 30 | 5.766606 | 6.217865 | 0.451259 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 대구광역시 | 24 | 5.174436 | 4.918174 | -0.256262 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 대전광역시 | 26 | 5.764056 | 5.829128 | 0.065072 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 부산광역시 | 48 | 7.001093 | 8.061561 | 1.060468 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 서울특별시 | 150 | 6.551131 | 6.951748 | 0.400617 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 울산광역시 | 15 | 6.641582 | 6.212278 | -0.429304 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 인천광역시 | 60 | 5.411448 | 5.432148 | 0.0207 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 전라남도 | 132 | 6.186474 | 6.242793 | 0.056319 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 전북특별자치도 | 83 | 3.723797 | 4.123662 | 0.399865 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 제주특별자치도 | 12 | 3.134762 | 3.869796 | 0.735034 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 충청남도 | 45 | 4.465287 | 4.120658 | -0.344629 |
| source_region | P1_fixed025_B4_relative_rel5_S1 | 충청북도 | 66 | 3.602157 | 3.349833 | -0.252324 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 강원특별자치도 | 54 | 5.102377 | 6.731901 | 1.629524 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 경기도 | 164 | 5.480317 | 5.581454 | 0.101137 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 경상남도 | 54 | 2.143597 | 2.829606 | 0.686009 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 경상북도 | 138 | 5.395846 | 5.025512 | -0.370334 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 광주광역시 | 30 | 5.355644 | 6.217865 | 0.862221 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 대구광역시 | 24 | 5.435472 | 4.918174 | -0.517298 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 대전광역시 | 26 | 5.705317 | 5.829128 | 0.123811 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 부산광역시 | 48 | 5.940625 | 8.061561 | 2.120936 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 서울특별시 | 150 | 6.211513 | 6.951748 | 0.740235 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 울산광역시 | 15 | 7.078693 | 6.212278 | -0.866415 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 인천광역시 | 60 | 5.533716 | 5.432148 | -0.101568 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 전라남도 | 132 | 6.316276 | 6.242793 | -0.073483 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 전북특별자치도 | 83 | 3.472983 | 4.123662 | 0.650679 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 제주특별자치도 | 12 | 2.975065 | 3.869796 | 0.894731 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 충청남도 | 45 | 4.871984 | 4.120658 | -0.751326 |
| source_region | P2_trainalpha_B4_relative_rel5_S1 | 충청북도 | 66 | 3.93862 | 3.349833 | -0.588787 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 강원특별자치도 | 54 | 6.535189 | 6.731901 | 0.196712 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 경기도 | 164 | 5.526678 | 5.581454 | 0.054776 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 경상남도 | 54 | 2.731317 | 2.829606 | 0.098289 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 경상북도 | 138 | 5.287761 | 5.025512 | -0.262249 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 광주광역시 | 30 | 6.032358 | 6.217865 | 0.185507 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 대구광역시 | 24 | 5.344045 | 4.918174 | -0.425871 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 대전광역시 | 26 | 6.197501 | 5.829128 | -0.368373 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 부산광역시 | 48 | 7.237128 | 8.061561 | 0.824433 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 서울특별시 | 150 | 7.074346 | 6.951748 | -0.122598 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 울산광역시 | 15 | 6.423376 | 6.212278 | -0.211098 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 인천광역시 | 60 | 5.435533 | 5.432148 | -0.003385 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 전라남도 | 132 | 6.467088 | 6.242793 | -0.224295 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 전북특별자치도 | 83 | 3.991815 | 4.123662 | 0.131847 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 제주특별자치도 | 12 | 4.08213 | 3.869796 | -0.212334 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 충청남도 | 45 | 4.295492 | 4.120658 | -0.174834 |
| source_region | P3_fixed025_B4_absolute_q95_S1 | 충청북도 | 66 | 3.481131 | 3.349833 | -0.131298 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 강원특별자치도 | 54 | 5.105127 | 6.731901 | 1.626774 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 경기도 | 164 | 5.172124 | 5.581454 | 0.40933 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 경상남도 | 54 | 2.139638 | 2.829606 | 0.689968 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 경상북도 | 138 | 4.917321 | 5.025512 | 0.108191 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 광주광역시 | 30 | 5.699462 | 6.217865 | 0.518403 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 대구광역시 | 24 | 5.422235 | 4.918174 | -0.504061 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 대전광역시 | 26 | 5.195189 | 5.829128 | 0.633939 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 부산광역시 | 48 | 5.952635 | 8.061561 | 2.108926 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 서울특별시 | 150 | 6.277611 | 6.951748 | 0.674137 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 울산광역시 | 15 | 7.063086 | 6.212278 | -0.850808 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 인천광역시 | 60 | 5.149196 | 5.432148 | 0.282952 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 전라남도 | 132 | 5.93846 | 6.242793 | 0.304333 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 전북특별자치도 | 83 | 3.405541 | 4.123662 | 0.718121 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 제주특별자치도 | 12 | 2.600002 | 3.869796 | 1.269794 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 충청남도 | 45 | 4.843643 | 4.120658 | -0.722985 |
| source_region | P4_trainalpha_B6_relative_rel5_S1 | 충청북도 | 66 | 4.102397 | 3.349833 | -0.752564 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 강원특별자치도 | 54 | 6.782207 | 6.731901 | -0.050306 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 경기도 | 164 | 5.520102 | 5.581454 | 0.061352 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 경상남도 | 54 | 2.979735 | 2.829606 | -0.150129 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 경상북도 | 138 | 5.17408 | 5.025512 | -0.148568 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 광주광역시 | 30 | 6.179035 | 6.217865 | 0.03883 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 대구광역시 | 24 | 5.081369 | 4.918174 | -0.163195 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 대전광역시 | 26 | 6.073065 | 5.829128 | -0.243937 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 부산광역시 | 48 | 7.79246 | 8.061561 | 0.269101 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 서울특별시 | 150 | 7.003321 | 6.951748 | -0.051573 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 울산광역시 | 15 | 6.50208 | 6.212278 | -0.289802 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 인천광역시 | 60 | 5.433119 | 5.432148 | -0.000971 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 전라남도 | 132 | 6.188314 | 6.242793 | 0.054479 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 전북특별자치도 | 83 | 4.21346 | 4.123662 | -0.089798 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 제주특별자치도 | 12 | 3.854398 | 3.869796 | 0.015398 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 충청남도 | 45 | 4.089961 | 4.120658 | 0.030697 |
| source_region | P5_trainalpha_B4_relative_rel5_S2_C00 | 충청북도 | 66 | 3.495826 | 3.349833 | -0.145993 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 강원특별자치도 | 54 | 5.490493 | 6.731901 | 1.241408 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 경기도 | 164 | 5.533985 | 5.581454 | 0.047469 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 경상남도 | 54 | 2.001104 | 2.829606 | 0.828502 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 경상북도 | 138 | 5.091428 | 5.025512 | -0.065916 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 광주광역시 | 30 | 5.59811 | 6.217865 | 0.619755 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 대구광역시 | 24 | 5.201974 | 4.918174 | -0.2838 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 대전광역시 | 26 | 5.857122 | 5.829128 | -0.027994 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 부산광역시 | 48 | 6.920508 | 8.061561 | 1.141053 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 서울특별시 | 150 | 6.537546 | 6.951748 | 0.414202 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 울산광역시 | 15 | 6.527302 | 6.212278 | -0.315024 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 인천광역시 | 60 | 5.647799 | 5.432148 | -0.215651 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 전라남도 | 132 | 6.21497 | 6.242793 | 0.027823 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 전북특별자치도 | 83 | 3.446415 | 4.123662 | 0.677247 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 제주특별자치도 | 12 | 3.686251 | 3.869796 | 0.183545 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 충청남도 | 45 | 4.330053 | 4.120658 | -0.209395 |
| source_region | P6_trainalpha_B4_relative_rel5_S3_all | 충청북도 | 66 | 3.386591 | 3.349833 | -0.036758 |
| source_region | bundle_B1_level_only | 강원특별자치도 | 54 | 5.107907 | 6.731901 | 1.623994 |
| source_region | bundle_B1_level_only | 경기도 | 164 | 5.418888 | 5.581454 | 0.162566 |
| source_region | bundle_B1_level_only | 경상남도 | 54 | 2.204125 | 2.829606 | 0.625481 |
| source_region | bundle_B1_level_only | 경상북도 | 138 | 5.367566 | 5.025512 | -0.342054 |
| source_region | bundle_B1_level_only | 광주광역시 | 30 | 5.404967 | 6.217865 | 0.812898 |
| source_region | bundle_B1_level_only | 대구광역시 | 24 | 5.383231 | 4.918174 | -0.465057 |
| source_region | bundle_B1_level_only | 대전광역시 | 26 | 5.684806 | 5.829128 | 0.144322 |
| source_region | bundle_B1_level_only | 부산광역시 | 48 | 5.946533 | 8.061561 | 2.115028 |
| source_region | bundle_B1_level_only | 서울특별시 | 150 | 6.228918 | 6.951748 | 0.72283 |
| source_region | bundle_B1_level_only | 울산광역시 | 15 | 7.071649 | 6.212278 | -0.859371 |
| source_region | bundle_B1_level_only | 인천광역시 | 60 | 5.468881 | 5.432148 | -0.036733 |
| source_region | bundle_B1_level_only | 전라남도 | 132 | 6.275477 | 6.242793 | -0.032684 |
| source_region | bundle_B1_level_only | 전북특별자치도 | 83 | 3.530919 | 4.123662 | 0.592743 |
| source_region | bundle_B1_level_only | 제주특별자치도 | 12 | 2.859017 | 3.869796 | 1.010779 |
| source_region | bundle_B1_level_only | 충청남도 | 45 | 4.713123 | 4.120658 | -0.592465 |
| source_region | bundle_B1_level_only | 충청북도 | 66 | 3.910621 | 3.349833 | -0.560788 |
| source_region | bundle_B3_composition_only | 강원특별자치도 | 54 | 5.14377 | 6.731901 | 1.588131 |
| source_region | bundle_B3_composition_only | 경기도 | 164 | 5.581236 | 5.581454 | 0.000218 |
| source_region | bundle_B3_composition_only | 경상남도 | 54 | 2.170629 | 2.829606 | 0.658977 |
| source_region | bundle_B3_composition_only | 경상북도 | 138 | 5.433437 | 5.025512 | -0.407925 |
| source_region | bundle_B3_composition_only | 광주광역시 | 30 | 5.308271 | 6.217865 | 0.909594 |
| source_region | bundle_B3_composition_only | 대구광역시 | 24 | 5.362682 | 4.918174 | -0.444508 |
| source_region | bundle_B3_composition_only | 대전광역시 | 26 | 5.766969 | 5.829128 | 0.062159 |
| source_region | bundle_B3_composition_only | 부산광역시 | 48 | 6.172401 | 8.061561 | 1.88916 |
| source_region | bundle_B3_composition_only | 서울특별시 | 150 | 6.223105 | 6.951748 | 0.728643 |
| source_region | bundle_B3_composition_only | 울산광역시 | 15 | 6.870015 | 6.212278 | -0.657737 |
| source_region | bundle_B3_composition_only | 인천광역시 | 60 | 5.703686 | 5.432148 | -0.271538 |
| source_region | bundle_B3_composition_only | 전라남도 | 132 | 6.381142 | 6.242793 | -0.138349 |
| source_region | bundle_B3_composition_only | 전북특별자치도 | 83 | 3.44789 | 4.123662 | 0.675772 |
| source_region | bundle_B3_composition_only | 제주특별자치도 | 12 | 3.293986 | 3.869796 | 0.57581 |
| source_region | bundle_B3_composition_only | 충청남도 | 45 | 4.717371 | 4.120658 | -0.596713 |
| source_region | bundle_B3_composition_only | 충청북도 | 66 | 3.793221 | 3.349833 | -0.443388 |
| source_region | bundle_B4_level_normalized | 강원특별자치도 | 54 | 5.102377 | 6.731901 | 1.629524 |
| source_region | bundle_B4_level_normalized | 경기도 | 164 | 5.480317 | 5.581454 | 0.101137 |
| source_region | bundle_B4_level_normalized | 경상남도 | 54 | 2.143597 | 2.829606 | 0.686009 |
| source_region | bundle_B4_level_normalized | 경상북도 | 138 | 5.395846 | 5.025512 | -0.370334 |
| source_region | bundle_B4_level_normalized | 광주광역시 | 30 | 5.355644 | 6.217865 | 0.862221 |
| source_region | bundle_B4_level_normalized | 대구광역시 | 24 | 5.435472 | 4.918174 | -0.517298 |
| source_region | bundle_B4_level_normalized | 대전광역시 | 26 | 5.705317 | 5.829128 | 0.123811 |
| source_region | bundle_B4_level_normalized | 부산광역시 | 48 | 5.940625 | 8.061561 | 2.120936 |
| source_region | bundle_B4_level_normalized | 서울특별시 | 150 | 6.211513 | 6.951748 | 0.740235 |
| source_region | bundle_B4_level_normalized | 울산광역시 | 15 | 7.078693 | 6.212278 | -0.866415 |
| source_region | bundle_B4_level_normalized | 인천광역시 | 60 | 5.533716 | 5.432148 | -0.101568 |
| source_region | bundle_B4_level_normalized | 전라남도 | 132 | 6.316276 | 6.242793 | -0.073483 |
| source_region | bundle_B4_level_normalized | 전북특별자치도 | 83 | 3.472983 | 4.123662 | 0.650679 |
| source_region | bundle_B4_level_normalized | 제주특별자치도 | 12 | 2.975065 | 3.869796 | 0.894731 |
| source_region | bundle_B4_level_normalized | 충청남도 | 45 | 4.871984 | 4.120658 | -0.751326 |
| source_region | bundle_B4_level_normalized | 충청북도 | 66 | 3.93862 | 3.349833 | -0.588787 |
| source_region | bundle_B5_full_minimal | 강원특별자치도 | 54 | 5.109529 | 6.731901 | 1.622372 |
| source_region | bundle_B5_full_minimal | 경기도 | 164 | 5.191801 | 5.581454 | 0.389653 |
| source_region | bundle_B5_full_minimal | 경상남도 | 54 | 2.139422 | 2.829606 | 0.690184 |
| source_region | bundle_B5_full_minimal | 경상북도 | 138 | 4.946735 | 5.025512 | 0.078777 |
| source_region | bundle_B5_full_minimal | 광주광역시 | 30 | 5.698356 | 6.217865 | 0.519509 |
| source_region | bundle_B5_full_minimal | 대구광역시 | 24 | 5.393618 | 4.918174 | -0.475444 |
| source_region | bundle_B5_full_minimal | 대전광역시 | 26 | 5.210458 | 5.829128 | 0.61867 |
| source_region | bundle_B5_full_minimal | 부산광역시 | 48 | 5.953694 | 8.061561 | 2.107867 |
| source_region | bundle_B5_full_minimal | 서울특별시 | 150 | 6.282712 | 6.951748 | 0.669036 |
| source_region | bundle_B5_full_minimal | 울산광역시 | 15 | 7.055818 | 6.212278 | -0.84354 |
| source_region | bundle_B5_full_minimal | 인천광역시 | 60 | 5.168276 | 5.432148 | 0.263872 |
| source_region | bundle_B5_full_minimal | 전라남도 | 132 | 5.942226 | 6.242793 | 0.300567 |
| source_region | bundle_B5_full_minimal | 전북특별자치도 | 83 | 3.404067 | 4.123662 | 0.719595 |
| source_region | bundle_B5_full_minimal | 제주특별자치도 | 12 | 2.592917 | 3.869796 | 1.276879 |
| source_region | bundle_B5_full_minimal | 충청남도 | 45 | 4.82819 | 4.120658 | -0.707532 |
| source_region | bundle_B5_full_minimal | 충청북도 | 66 | 4.099864 | 3.349833 | -0.750031 |
| source_region | bundle_B6_full_without_change | 강원특별자치도 | 54 | 5.105127 | 6.731901 | 1.626774 |
| source_region | bundle_B6_full_without_change | 경기도 | 164 | 5.172124 | 5.581454 | 0.40933 |
| source_region | bundle_B6_full_without_change | 경상남도 | 54 | 2.139638 | 2.829606 | 0.689968 |
| source_region | bundle_B6_full_without_change | 경상북도 | 138 | 4.917321 | 5.025512 | 0.108191 |
| source_region | bundle_B6_full_without_change | 광주광역시 | 30 | 5.699462 | 6.217865 | 0.518403 |
| source_region | bundle_B6_full_without_change | 대구광역시 | 24 | 5.422235 | 4.918174 | -0.504061 |
| source_region | bundle_B6_full_without_change | 대전광역시 | 26 | 5.195189 | 5.829128 | 0.633939 |
| source_region | bundle_B6_full_without_change | 부산광역시 | 48 | 5.952635 | 8.061561 | 2.108926 |
| source_region | bundle_B6_full_without_change | 서울특별시 | 150 | 6.277611 | 6.951748 | 0.674137 |
| source_region | bundle_B6_full_without_change | 울산광역시 | 15 | 7.063086 | 6.212278 | -0.850808 |
| source_region | bundle_B6_full_without_change | 인천광역시 | 60 | 5.149196 | 5.432148 | 0.282952 |
| source_region | bundle_B6_full_without_change | 전라남도 | 132 | 5.93846 | 6.242793 | 0.304333 |
| source_region | bundle_B6_full_without_change | 전북특별자치도 | 83 | 3.405541 | 4.123662 | 0.718121 |
| source_region | bundle_B6_full_without_change | 제주특별자치도 | 12 | 2.600002 | 3.869796 | 1.269794 |
| source_region | bundle_B6_full_without_change | 충청남도 | 45 | 4.843643 | 4.120658 | -0.722985 |
| source_region | bundle_B6_full_without_change | 충청북도 | 66 | 4.102397 | 3.349833 | -0.752564 |
| source_region | bundle_B7_normalized_only | 강원특별자치도 | 54 | 5.14377 | 6.731901 | 1.588131 |
| source_region | bundle_B7_normalized_only | 경기도 | 164 | 5.581236 | 5.581454 | 0.000218 |
| source_region | bundle_B7_normalized_only | 경상남도 | 54 | 2.170629 | 2.829606 | 0.658977 |
| source_region | bundle_B7_normalized_only | 경상북도 | 138 | 5.433437 | 5.025512 | -0.407925 |
| source_region | bundle_B7_normalized_only | 광주광역시 | 30 | 5.308271 | 6.217865 | 0.909594 |
| source_region | bundle_B7_normalized_only | 대구광역시 | 24 | 5.362682 | 4.918174 | -0.444508 |
| source_region | bundle_B7_normalized_only | 대전광역시 | 26 | 5.766969 | 5.829128 | 0.062159 |
| source_region | bundle_B7_normalized_only | 부산광역시 | 48 | 6.172401 | 8.061561 | 1.88916 |
| source_region | bundle_B7_normalized_only | 서울특별시 | 150 | 6.223105 | 6.951748 | 0.728643 |
| source_region | bundle_B7_normalized_only | 울산광역시 | 15 | 6.870015 | 6.212278 | -0.657737 |
| source_region | bundle_B7_normalized_only | 인천광역시 | 60 | 5.703686 | 5.432148 | -0.271538 |
| source_region | bundle_B7_normalized_only | 전라남도 | 132 | 6.381142 | 6.242793 | -0.138349 |
| source_region | bundle_B7_normalized_only | 전북특별자치도 | 83 | 3.44789 | 4.123662 | 0.675772 |
| source_region | bundle_B7_normalized_only | 제주특별자치도 | 12 | 3.293986 | 3.869796 | 0.57581 |
| source_region | bundle_B7_normalized_only | 충청남도 | 45 | 4.717371 | 4.120658 | -0.596713 |
| source_region | bundle_B7_normalized_only | 충청북도 | 66 | 3.793221 | 3.349833 | -0.443388 |
| source_region | bundle_B8_change_only_negative_control | 강원특별자치도 | 54 | 5.078671 | 6.731901 | 1.65323 |
| source_region | bundle_B8_change_only_negative_control | 경기도 | 164 | 5.883033 | 5.581454 | -0.301579 |
| source_region | bundle_B8_change_only_negative_control | 경상남도 | 54 | 2.42068 | 2.829606 | 0.408926 |
| source_region | bundle_B8_change_only_negative_control | 경상북도 | 138 | 5.863252 | 5.025512 | -0.83774 |
| source_region | bundle_B8_change_only_negative_control | 광주광역시 | 30 | 5.142789 | 6.217865 | 1.075076 |
| source_region | bundle_B8_change_only_negative_control | 대구광역시 | 24 | 5.699608 | 4.918174 | -0.781434 |
| source_region | bundle_B8_change_only_negative_control | 대전광역시 | 26 | 5.823691 | 5.829128 | 0.005437 |
| source_region | bundle_B8_change_only_negative_control | 부산광역시 | 48 | 5.852961 | 8.061561 | 2.2086 |
| source_region | bundle_B8_change_only_negative_control | 서울특별시 | 150 | 6.352575 | 6.951748 | 0.599173 |
| source_region | bundle_B8_change_only_negative_control | 울산광역시 | 15 | 7.238874 | 6.212278 | -1.026596 |
| source_region | bundle_B8_change_only_negative_control | 인천광역시 | 60 | 5.672062 | 5.432148 | -0.239914 |
| source_region | bundle_B8_change_only_negative_control | 전라남도 | 132 | 6.745522 | 6.242793 | -0.502729 |
| source_region | bundle_B8_change_only_negative_control | 전북특별자치도 | 83 | 3.429743 | 4.123662 | 0.693919 |
| source_region | bundle_B8_change_only_negative_control | 제주특별자치도 | 12 | 3.013963 | 3.869796 | 0.855833 |
| source_region | bundle_B8_change_only_negative_control | 충청남도 | 45 | 5.49291 | 4.120658 | -1.372252 |
| source_region | bundle_B8_change_only_negative_control | 충청북도 | 66 | 4.056563 | 3.349833 | -0.70673 |
| source_region | clip_q90 | 강원특별자치도 | 54 | 4.835397 | 6.731901 | 1.896504 |
| source_region | clip_q90 | 경기도 | 164 | 5.420943 | 5.581454 | 0.160511 |
| source_region | clip_q90 | 경상남도 | 54 | 2.373078 | 2.829606 | 0.456528 |
| source_region | clip_q90 | 경상북도 | 138 | 5.298927 | 5.025512 | -0.273415 |
| source_region | clip_q90 | 광주광역시 | 30 | 5.40138 | 6.217865 | 0.816485 |
| source_region | clip_q90 | 대구광역시 | 24 | 5.314387 | 4.918174 | -0.396213 |
| source_region | clip_q90 | 대전광역시 | 26 | 5.525605 | 5.829128 | 0.303523 |
| source_region | clip_q90 | 부산광역시 | 48 | 5.611757 | 8.061561 | 2.449804 |
| source_region | clip_q90 | 서울특별시 | 150 | 6.540441 | 6.951748 | 0.411307 |
| source_region | clip_q90 | 울산광역시 | 15 | 7.040297 | 6.212278 | -0.828019 |
| source_region | clip_q90 | 인천광역시 | 60 | 5.462075 | 5.432148 | -0.029927 |
| source_region | clip_q90 | 전라남도 | 132 | 6.345297 | 6.242793 | -0.102504 |
| source_region | clip_q90 | 전북특별자치도 | 83 | 3.481511 | 4.123662 | 0.642151 |
| source_region | clip_q90 | 제주특별자치도 | 12 | 2.790871 | 3.869796 | 1.078925 |
| source_region | clip_q90 | 충청남도 | 45 | 4.585984 | 4.120658 | -0.465326 |
| source_region | clip_q90 | 충청북도 | 66 | 3.824851 | 3.349833 | -0.475018 |
| source_region | clip_q95 | 강원특별자치도 | 54 | 4.835397 | 6.731901 | 1.896504 |
| source_region | clip_q95 | 경기도 | 164 | 5.417601 | 5.581454 | 0.163853 |
| source_region | clip_q95 | 경상남도 | 54 | 2.319435 | 2.829606 | 0.510171 |
| source_region | clip_q95 | 경상북도 | 138 | 5.371631 | 5.025512 | -0.346119 |
| source_region | clip_q95 | 광주광역시 | 30 | 5.349825 | 6.217865 | 0.86804 |
| source_region | clip_q95 | 대구광역시 | 24 | 5.314387 | 4.918174 | -0.396213 |
| source_region | clip_q95 | 대전광역시 | 26 | 5.520905 | 5.829128 | 0.308223 |
| source_region | clip_q95 | 부산광역시 | 48 | 5.611757 | 8.061561 | 2.449804 |
| source_region | clip_q95 | 서울특별시 | 150 | 6.508689 | 6.951748 | 0.443059 |
| source_region | clip_q95 | 울산광역시 | 15 | 7.105823 | 6.212278 | -0.893545 |
| source_region | clip_q95 | 인천광역시 | 60 | 5.50807 | 5.432148 | -0.075922 |
| source_region | clip_q95 | 전라남도 | 132 | 6.345297 | 6.242793 | -0.102504 |
| source_region | clip_q95 | 전북특별자치도 | 83 | 3.481511 | 4.123662 | 0.642151 |
| source_region | clip_q95 | 제주특별자치도 | 12 | 2.778548 | 3.869796 | 1.091248 |
| source_region | clip_q95 | 충청남도 | 45 | 4.768785 | 4.120658 | -0.648127 |
| source_region | clip_q95 | 충청북도 | 66 | 3.883766 | 3.349833 | -0.533933 |
| source_region | clip_q99 | 강원특별자치도 | 54 | 4.835397 | 6.731901 | 1.896504 |
| source_region | clip_q99 | 경기도 | 164 | 5.440637 | 5.581454 | 0.140817 |
| source_region | clip_q99 | 경상남도 | 54 | 2.166439 | 2.829606 | 0.663167 |
| source_region | clip_q99 | 경상북도 | 138 | 5.388452 | 5.025512 | -0.36294 |
| source_region | clip_q99 | 광주광역시 | 30 | 5.349825 | 6.217865 | 0.86804 |
| source_region | clip_q99 | 대구광역시 | 24 | 5.314387 | 4.918174 | -0.396213 |
| source_region | clip_q99 | 대전광역시 | 26 | 5.520905 | 5.829128 | 0.308223 |
| source_region | clip_q99 | 부산광역시 | 48 | 5.611757 | 8.061561 | 2.449804 |
| source_region | clip_q99 | 서울특별시 | 150 | 6.35338 | 6.951748 | 0.598368 |
| source_region | clip_q99 | 울산광역시 | 15 | 7.105823 | 6.212278 | -0.893545 |
| source_region | clip_q99 | 인천광역시 | 60 | 5.50807 | 5.432148 | -0.075922 |
| source_region | clip_q99 | 전라남도 | 132 | 6.345297 | 6.242793 | -0.102504 |
| source_region | clip_q99 | 전북특별자치도 | 83 | 3.481511 | 4.123662 | 0.642151 |
| source_region | clip_q99 | 제주특별자치도 | 12 | 2.783076 | 3.869796 | 1.08672 |
| source_region | clip_q99 | 충청남도 | 45 | 4.862354 | 4.120658 | -0.741696 |
| source_region | clip_q99 | 충청북도 | 66 | 3.93762 | 3.349833 | -0.587787 |
| source_region | clip_rel0.02 | 강원특별자치도 | 54 | 5.957036 | 6.731901 | 0.774865 |
| source_region | clip_rel0.02 | 경기도 | 164 | 5.599787 | 5.581454 | -0.018333 |
| source_region | clip_rel0.02 | 경상남도 | 54 | 2.465343 | 2.829606 | 0.364263 |
| source_region | clip_rel0.02 | 경상북도 | 138 | 5.280185 | 5.025512 | -0.254673 |
| source_region | clip_rel0.02 | 광주광역시 | 30 | 5.690114 | 6.217865 | 0.527751 |
| source_region | clip_rel0.02 | 대구광역시 | 24 | 5.197237 | 4.918174 | -0.279063 |
| source_region | clip_rel0.02 | 대전광역시 | 26 | 5.925672 | 5.829128 | -0.096544 |
| source_region | clip_rel0.02 | 부산광역시 | 48 | 7.14301 | 8.061561 | 0.918551 |
| source_region | clip_rel0.02 | 서울특별시 | 150 | 6.60663 | 6.951748 | 0.345118 |
| source_region | clip_rel0.02 | 울산광역시 | 15 | 6.62246 | 6.212278 | -0.410182 |
| source_region | clip_rel0.02 | 인천광역시 | 60 | 5.51102 | 5.432148 | -0.078872 |
| source_region | clip_rel0.02 | 전라남도 | 132 | 6.276773 | 6.242793 | -0.03398 |
| source_region | clip_rel0.02 | 전북특별자치도 | 83 | 3.779749 | 4.123662 | 0.343913 |
| source_region | clip_rel0.02 | 제주특별자치도 | 12 | 3.302827 | 3.869796 | 0.566969 |
| source_region | clip_rel0.02 | 충청남도 | 45 | 4.64106 | 4.120658 | -0.520402 |
| source_region | clip_rel0.02 | 충청북도 | 66 | 3.643364 | 3.349833 | -0.293531 |
| source_region | clip_rel0.05 | 강원특별자치도 | 54 | 5.102377 | 6.731901 | 1.629524 |
| source_region | clip_rel0.05 | 경기도 | 164 | 5.480317 | 5.581454 | 0.101137 |
| source_region | clip_rel0.05 | 경상남도 | 54 | 2.143597 | 2.829606 | 0.686009 |
| source_region | clip_rel0.05 | 경상북도 | 138 | 5.395846 | 5.025512 | -0.370334 |
| source_region | clip_rel0.05 | 광주광역시 | 30 | 5.355644 | 6.217865 | 0.862221 |
| source_region | clip_rel0.05 | 대구광역시 | 24 | 5.435472 | 4.918174 | -0.517298 |
| source_region | clip_rel0.05 | 대전광역시 | 26 | 5.705317 | 5.829128 | 0.123811 |
| source_region | clip_rel0.05 | 부산광역시 | 48 | 5.940625 | 8.061561 | 2.120936 |
| source_region | clip_rel0.05 | 서울특별시 | 150 | 6.211513 | 6.951748 | 0.740235 |
| source_region | clip_rel0.05 | 울산광역시 | 15 | 7.078693 | 6.212278 | -0.866415 |
| source_region | clip_rel0.05 | 인천광역시 | 60 | 5.533716 | 5.432148 | -0.101568 |
| source_region | clip_rel0.05 | 전라남도 | 132 | 6.316276 | 6.242793 | -0.073483 |
| source_region | clip_rel0.05 | 전북특별자치도 | 83 | 3.472983 | 4.123662 | 0.650679 |
| source_region | clip_rel0.05 | 제주특별자치도 | 12 | 2.975065 | 3.869796 | 0.894731 |
| source_region | clip_rel0.05 | 충청남도 | 45 | 4.871984 | 4.120658 | -0.751326 |
| source_region | clip_rel0.05 | 충청북도 | 66 | 3.93862 | 3.349833 | -0.588787 |
| source_region | clip_rel0.10 | 강원특별자치도 | 54 | 4.835397 | 6.731901 | 1.896504 |
| source_region | clip_rel0.10 | 경기도 | 164 | 5.476481 | 5.581454 | 0.104973 |
| source_region | clip_rel0.10 | 경상남도 | 54 | 2.166439 | 2.829606 | 0.663167 |
| source_region | clip_rel0.10 | 경상북도 | 138 | 5.388452 | 5.025512 | -0.36294 |
| source_region | clip_rel0.10 | 광주광역시 | 30 | 5.349825 | 6.217865 | 0.86804 |
| source_region | clip_rel0.10 | 대구광역시 | 24 | 5.314387 | 4.918174 | -0.396213 |
| source_region | clip_rel0.10 | 대전광역시 | 26 | 5.520905 | 5.829128 | 0.308223 |
| source_region | clip_rel0.10 | 부산광역시 | 48 | 5.611757 | 8.061561 | 2.449804 |
| source_region | clip_rel0.10 | 서울특별시 | 150 | 6.113888 | 6.951748 | 0.83786 |
| source_region | clip_rel0.10 | 울산광역시 | 15 | 7.105823 | 6.212278 | -0.893545 |
| source_region | clip_rel0.10 | 인천광역시 | 60 | 5.50807 | 5.432148 | -0.075922 |
| source_region | clip_rel0.10 | 전라남도 | 132 | 6.345297 | 6.242793 | -0.102504 |
| source_region | clip_rel0.10 | 전북특별자치도 | 83 | 3.481511 | 4.123662 | 0.642151 |
| source_region | clip_rel0.10 | 제주특별자치도 | 12 | 2.783076 | 3.869796 | 1.08672 |
| source_region | clip_rel0.10 | 충청남도 | 45 | 4.862354 | 4.120658 | -0.741696 |
| source_region | clip_rel0.10 | 충청북도 | 66 | 3.93762 | 3.349833 | -0.587787 |
| source_region | mask_S0_all_apply | 강원특별자치도 | 54 | 6.731901 | 6.731901 | 0.0 |
| source_region | mask_S0_all_apply | 경기도 | 164 | 5.3496 | 5.581454 | 0.231854 |
| source_region | mask_S0_all_apply | 경상남도 | 54 | 2.829606 | 2.829606 | 0.0 |
| source_region | mask_S0_all_apply | 경상북도 | 138 | 4.650861 | 5.025512 | 0.374651 |
| source_region | mask_S0_all_apply | 광주광역시 | 30 | 6.303844 | 6.217865 | -0.085979 |
| source_region | mask_S0_all_apply | 대구광역시 | 24 | 4.918174 | 4.918174 | -0.0 |
| source_region | mask_S0_all_apply | 대전광역시 | 26 | 5.917482 | 5.829128 | -0.088354 |
| source_region | mask_S0_all_apply | 부산광역시 | 48 | 8.061561 | 8.061561 | 0.0 |
| source_region | mask_S0_all_apply | 서울특별시 | 150 | 6.838068 | 6.951748 | 0.11368 |
| source_region | mask_S0_all_apply | 울산광역시 | 15 | 6.212278 | 6.212278 | 0.0 |
| source_region | mask_S0_all_apply | 인천광역시 | 60 | 5.485959 | 5.432148 | -0.053811 |
| source_region | mask_S0_all_apply | 전라남도 | 132 | 5.847706 | 6.242793 | 0.395087 |
| source_region | mask_S0_all_apply | 전북특별자치도 | 83 | 4.108775 | 4.123662 | 0.014887 |
| source_region | mask_S0_all_apply | 제주특별자치도 | 12 | 3.898201 | 3.869796 | -0.028405 |
| source_region | mask_S0_all_apply | 충청남도 | 45 | 4.120658 | 4.120658 | 0.0 |
| source_region | mask_S0_all_apply | 충청북도 | 66 | 3.502388 | 3.349833 | -0.152555 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 강원특별자치도 | 54 | 5.102377 | 6.731901 | 1.629524 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 경기도 | 164 | 5.480317 | 5.581454 | 0.101137 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 경상남도 | 54 | 2.143597 | 2.829606 | 0.686009 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 경상북도 | 138 | 5.395846 | 5.025512 | -0.370334 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 광주광역시 | 30 | 5.355644 | 6.217865 | 0.862221 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 대구광역시 | 24 | 5.435472 | 4.918174 | -0.517298 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 대전광역시 | 26 | 5.705317 | 5.829128 | 0.123811 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 부산광역시 | 48 | 5.940625 | 8.061561 | 2.120936 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 서울특별시 | 150 | 6.211513 | 6.951748 | 0.740235 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 울산광역시 | 15 | 7.078693 | 6.212278 | -0.866415 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 인천광역시 | 60 | 5.533716 | 5.432148 | -0.101568 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 전라남도 | 132 | 6.316276 | 6.242793 | -0.073483 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 전북특별자치도 | 83 | 3.472983 | 4.123662 | 0.650679 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 제주특별자치도 | 12 | 2.975065 | 3.869796 | 0.894731 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 충청남도 | 45 | 4.871984 | 4.120658 | -0.751326 |
| source_region | mask_S1_C00_all_apply_D00_fallback | 충청북도 | 66 | 3.93862 | 3.349833 | -0.588787 |
| source_region | mask_S2_C00_only | 강원특별자치도 | 54 | 6.782207 | 6.731901 | -0.050306 |
| source_region | mask_S2_C00_only | 경기도 | 164 | 5.520102 | 5.581454 | 0.061352 |
| source_region | mask_S2_C00_only | 경상남도 | 54 | 2.979735 | 2.829606 | -0.150129 |
| source_region | mask_S2_C00_only | 경상북도 | 138 | 5.17408 | 5.025512 | -0.148568 |
| source_region | mask_S2_C00_only | 광주광역시 | 30 | 6.179035 | 6.217865 | 0.03883 |
| source_region | mask_S2_C00_only | 대구광역시 | 24 | 5.081369 | 4.918174 | -0.163195 |
| source_region | mask_S2_C00_only | 대전광역시 | 26 | 6.073065 | 5.829128 | -0.243937 |
| source_region | mask_S2_C00_only | 부산광역시 | 48 | 7.79246 | 8.061561 | 0.269101 |
| source_region | mask_S2_C00_only | 서울특별시 | 150 | 7.003321 | 6.951748 | -0.051573 |
| source_region | mask_S2_C00_only | 울산광역시 | 15 | 6.50208 | 6.212278 | -0.289802 |
| source_region | mask_S2_C00_only | 인천광역시 | 60 | 5.433119 | 5.432148 | -0.000971 |
| source_region | mask_S2_C00_only | 전라남도 | 132 | 6.188314 | 6.242793 | 0.054479 |
| source_region | mask_S2_C00_only | 전북특별자치도 | 83 | 4.21346 | 4.123662 | -0.089798 |
| source_region | mask_S2_C00_only | 제주특별자치도 | 12 | 3.854398 | 3.869796 | 0.015398 |
| source_region | mask_S2_C00_only | 충청남도 | 45 | 4.089961 | 4.120658 | 0.030697 |
| source_region | mask_S2_C00_only | 충청북도 | 66 | 3.495826 | 3.349833 | -0.145993 |
| source_region | mask_S3_all_only | 강원특별자치도 | 54 | 5.490493 | 6.731901 | 1.241408 |
| source_region | mask_S3_all_only | 경기도 | 164 | 5.533985 | 5.581454 | 0.047469 |
| source_region | mask_S3_all_only | 경상남도 | 54 | 2.001104 | 2.829606 | 0.828502 |
| source_region | mask_S3_all_only | 경상북도 | 138 | 5.091428 | 5.025512 | -0.065916 |
| source_region | mask_S3_all_only | 광주광역시 | 30 | 5.59811 | 6.217865 | 0.619755 |
| source_region | mask_S3_all_only | 대구광역시 | 24 | 5.201974 | 4.918174 | -0.2838 |
| source_region | mask_S3_all_only | 대전광역시 | 26 | 5.857122 | 5.829128 | -0.027994 |
| source_region | mask_S3_all_only | 부산광역시 | 48 | 6.920508 | 8.061561 | 1.141053 |
| source_region | mask_S3_all_only | 서울특별시 | 150 | 6.537546 | 6.951748 | 0.414202 |
| source_region | mask_S3_all_only | 울산광역시 | 15 | 6.527302 | 6.212278 | -0.315024 |
| source_region | mask_S3_all_only | 인천광역시 | 60 | 5.647799 | 5.432148 | -0.215651 |
| source_region | mask_S3_all_only | 전라남도 | 132 | 6.21497 | 6.242793 | 0.027823 |
| source_region | mask_S3_all_only | 전북특별자치도 | 83 | 3.446415 | 4.123662 | 0.677247 |
| source_region | mask_S3_all_only | 제주특별자치도 | 12 | 3.686251 | 3.869796 | 0.183545 |
| source_region | mask_S3_all_only | 충청남도 | 45 | 4.330053 | 4.120658 | -0.209395 |
| source_region | mask_S3_all_only | 충청북도 | 66 | 3.386591 | 3.349833 | -0.036758 |
| source_region | target_absolute | 강원특별자치도 | 54 | 5.7754 | 6.731901 | 0.956501 |
| source_region | target_absolute | 경기도 | 164 | 5.490675 | 5.581454 | 0.090779 |
| source_region | target_absolute | 경상남도 | 54 | 2.576888 | 2.829606 | 0.252718 |
| source_region | target_absolute | 경상북도 | 138 | 5.246323 | 5.025512 | -0.220811 |
| source_region | target_absolute | 광주광역시 | 30 | 5.691002 | 6.217865 | 0.526863 |
| source_region | target_absolute | 대구광역시 | 24 | 5.564105 | 4.918174 | -0.645931 |
| source_region | target_absolute | 대전광역시 | 26 | 5.994349 | 5.829128 | -0.165221 |
| source_region | target_absolute | 부산광역시 | 48 | 6.509068 | 8.061561 | 1.552493 |
| source_region | target_absolute | 서울특별시 | 150 | 6.750786 | 6.951748 | 0.200962 |
| source_region | target_absolute | 울산광역시 | 15 | 6.63821 | 6.212278 | -0.425932 |
| source_region | target_absolute | 인천광역시 | 60 | 5.468856 | 5.432148 | -0.036708 |
| source_region | target_absolute | 전라남도 | 132 | 6.329802 | 6.242793 | -0.087009 |
| source_region | target_absolute | 전북특별자치도 | 83 | 3.727267 | 4.123662 | 0.396395 |
| source_region | target_absolute | 제주특별자치도 | 12 | 3.331823 | 3.869796 | 0.537973 |
| source_region | target_absolute | 충청남도 | 45 | 4.442385 | 4.120658 | -0.321727 |
| source_region | target_absolute | 충청북도 | 66 | 3.691469 | 3.349833 | -0.341636 |
| source_region | target_log_ratio | 강원특별자치도 | 54 | 5.093221 | 6.731901 | 1.63868 |
| source_region | target_log_ratio | 경기도 | 164 | 5.492504 | 5.581454 | 0.08895 |
| source_region | target_log_ratio | 경상남도 | 54 | 2.147212 | 2.829606 | 0.682394 |
| source_region | target_log_ratio | 경상북도 | 138 | 5.461932 | 5.025512 | -0.43642 |
| source_region | target_log_ratio | 광주광역시 | 30 | 5.271084 | 6.217865 | 0.946781 |
| source_region | target_log_ratio | 대구광역시 | 24 | 5.530018 | 4.918174 | -0.611844 |
| source_region | target_log_ratio | 대전광역시 | 26 | 5.786723 | 5.829128 | 0.042405 |
| source_region | target_log_ratio | 부산광역시 | 48 | 5.875749 | 8.061561 | 2.185812 |
| source_region | target_log_ratio | 서울특별시 | 150 | 6.225284 | 6.951748 | 0.726464 |
| source_region | target_log_ratio | 울산광역시 | 15 | 7.139897 | 6.212278 | -0.927619 |
| source_region | target_log_ratio | 인천광역시 | 60 | 5.586404 | 5.432148 | -0.154256 |
| source_region | target_log_ratio | 전라남도 | 132 | 6.340766 | 6.242793 | -0.097973 |
| source_region | target_log_ratio | 전북특별자치도 | 83 | 3.475833 | 4.123662 | 0.647829 |
| source_region | target_log_ratio | 제주특별자치도 | 12 | 3.101713 | 3.869796 | 0.768083 |
| source_region | target_log_ratio | 충청남도 | 45 | 4.933427 | 4.120658 | -0.812769 |
| source_region | target_log_ratio | 충청북도 | 66 | 4.002368 | 3.349833 | -0.652535 |
| source_region | target_relative | 강원특별자치도 | 54 | 5.102377 | 6.731901 | 1.629524 |
| source_region | target_relative | 경기도 | 164 | 5.480317 | 5.581454 | 0.101137 |
| source_region | target_relative | 경상남도 | 54 | 2.143597 | 2.829606 | 0.686009 |
| source_region | target_relative | 경상북도 | 138 | 5.395846 | 5.025512 | -0.370334 |
| source_region | target_relative | 광주광역시 | 30 | 5.355644 | 6.217865 | 0.862221 |
| source_region | target_relative | 대구광역시 | 24 | 5.435472 | 4.918174 | -0.517298 |
| source_region | target_relative | 대전광역시 | 26 | 5.705317 | 5.829128 | 0.123811 |
| source_region | target_relative | 부산광역시 | 48 | 5.940625 | 8.061561 | 2.120936 |
| source_region | target_relative | 서울특별시 | 150 | 6.211513 | 6.951748 | 0.740235 |
| source_region | target_relative | 울산광역시 | 15 | 7.078693 | 6.212278 | -0.866415 |
| source_region | target_relative | 인천광역시 | 60 | 5.533716 | 5.432148 | -0.101568 |
| source_region | target_relative | 전라남도 | 132 | 6.316276 | 6.242793 | -0.073483 |
| source_region | target_relative | 전북특별자치도 | 83 | 3.472983 | 4.123662 | 0.650679 |
| source_region | target_relative | 제주특별자치도 | 12 | 2.975065 | 3.869796 | 0.894731 |
| source_region | target_relative | 충청남도 | 45 | 4.871984 | 4.120658 | -0.751326 |
| source_region | target_relative | 충청북도 | 66 | 3.93862 | 3.349833 | -0.588787 |

## 5. Alpha 선택 로그

| policy | origin | test_year | alpha | validation WMAPE | count |
| --- | --- | ---: | ---: | ---: | ---: |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.0 | 5.45301 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.05 | 5.346779 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.1 | 5.24236 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.15 | 5.141395 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.2 | 5.043815 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.25 | 4.950125 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.3 | 4.866988 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.4 | 4.716147 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2022 | 0.5 | 4.592865 | 672 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.0 | 5.849244 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.05 | 5.782706 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.1 | 5.723841 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.15 | 5.669371 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.2 | 5.617368 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.25 | 5.572387 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.3 | 5.532973 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.4 | 5.471175 | 671 |
| P2_trainalpha_B4_relative_rel5_S1 | O1 | 2023 | 0.5 | 5.435939 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.0 | 5.45301 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.05 | 5.34808 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.1 | 5.244962 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.15 | 5.145258 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.2 | 5.04896 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.25 | 4.956555 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.3 | 4.873255 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.4 | 4.72346 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2022 | 0.5 | 4.599496 | 672 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.0 | 5.849244 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.05 | 5.782361 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.1 | 5.723115 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.15 | 5.668282 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.2 | 5.615604 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.25 | 5.5691 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.3 | 5.529028 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.4 | 5.463951 | 671 |
| P4_trainalpha_B6_relative_rel5_S1 | O1 | 2023 | 0.5 | 5.426617 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.0 | 5.45301 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.05 | 5.421932 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.1 | 5.391119 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.15 | 5.363769 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.2 | 5.347023 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.25 | 5.331569 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.3 | 5.317242 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.4 | 5.29333 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2022 | 0.5 | 5.26975 | 672 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.0 | 5.849244 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.05 | 5.847222 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.1 | 5.846943 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.15 | 5.84744 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.2 | 5.848949 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.25 | 5.851107 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.3 | 5.853349 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.4 | 5.860519 | 671 |
| P5_trainalpha_B4_relative_rel5_S2_C00 | O1 | 2023 | 0.5 | 5.870235 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.0 | 5.45301 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.05 | 5.403025 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.1 | 5.353521 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.15 | 5.305906 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.2 | 5.258951 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.25 | 5.212233 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.3 | 5.167386 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.4 | 5.094116 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2022 | 0.5 | 5.036847 | 672 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.0 | 5.849244 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.05 | 5.800679 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.1 | 5.754354 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.15 | 5.709014 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.2 | 5.664895 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.25 | 5.621908 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.3 | 5.579099 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.4 | 5.501149 | 671 |
| P6_trainalpha_B4_relative_rel5_S3_all | O1 | 2023 | 0.5 | 5.431686 | 671 |
| bundle_B1_level_only | O1 | 2022 | 0.0 | 5.45301 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.05 | 5.358635 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.1 | 5.266117 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.15 | 5.177059 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.2 | 5.09105 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.25 | 5.009178 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.3 | 4.930129 | 672 |
| bundle_B1_level_only | O1 | 2022 | 0.4 | 4.780267 | 672 |

## 6. Bootstrap

| scope | group | iterations | mean delta | CI 2.5 | CI 97.5 | P(improve) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pooled | sigungu_feature_key | 2000 | 0.319456 | 0.114481 | 0.529643 | 0.999 |
| pooled_industry_year | sector_code | 2000 | 0.229813 | -0.241954 | 0.565889 | 0.7095 |
| year_2022 | sigungu_feature_key | 2000 | 0.43671 | 0.057758 | 0.842754 | 0.988 |
| year_2022_industry_year | sector_code | 2000 | 0.270049 | -0.561803 | 0.859602 | 0.707 |
| year_2023 | sigungu_feature_key | 2000 | 0.167854 | -0.012771 | 0.350589 | 0.9665 |
| year_2023_industry_year | sector_code | 2000 | 0.171377 | 0.0 | 0.218846 | 0.9585 |
| sector_C00 | sigungu_feature_key | 2000 | -0.241076 | -0.475277 | -0.008925 | 0.021 |
| sector_C00_industry_year | sector_code | 2000 | -0.241954 | -0.241954 | -0.241954 | 0.0 |
| sector_D00 | sigungu_feature_key | 2000 | 0.0 | 0.0 | 0.0 | 0.0 |
| sector_D00_industry_year | sector_code | 2000 | 0.0 | 0.0 | 0.0 | 0.0 |
| sector_all | sigungu_feature_key | 2000 | 0.572475 | 0.338788 | 0.80777 | 1.0 |
| sector_all_industry_year | sector_code | 2000 | 0.565889 | 0.565889 | 0.565889 | 1.0 |

## 7. Leave-One-Sido-Out

| heldout | count | global WMAPE | candidate WMAPE | delta +good | status |
| --- | ---: | ---: | ---: | ---: | --- |
| 강원특별자치도 | 54 | 6.731901 | 6.18865 | 0.543251 | fit |
| 경기도 | 164 | 5.581454 | 5.386739 | 0.194715 | fit |
| 경상남도 | 54 | 2.829606 | 2.691596 | 0.13801 | fit |
| 경상북도 | 138 | 5.025512 | 4.939031 | 0.086481 | fit |
| 광주광역시 | 30 | 6.217865 | 6.105049 | 0.112816 | fit |
| 대구광역시 | 24 | 4.918174 | 4.929888 | -0.011714 | fit |
| 대전광역시 | 26 | 5.829128 | 5.658764 | 0.170363 | fit |
| 부산광역시 | 48 | 8.061561 | 7.586248 | 0.475313 | fit |
| 서울특별시 | 150 | 6.951748 | 6.662113 | 0.289634 | fit |
| 울산광역시 | 15 | 6.212278 | 6.361458 | -0.149179 | fit |
| 인천광역시 | 60 | 5.432148 | 5.40187 | 0.030278 | fit |
| 전라남도 | 132 | 6.242793 | 6.115916 | 0.126877 | fit |
| 전북특별자치도 | 83 | 4.123662 | 3.980084 | 0.143578 | fit |
| 제주특별자치도 | 12 | 3.869796 | 3.511054 | 0.358742 | fit |
| 충청남도 | 45 | 4.120658 | 4.098366 | 0.022292 | fit |
| 충청북도 | 66 | 3.349833 | 3.439582 | -0.089749 | fit |

## 8. Placebo

| placebo | iterations | real delta | placebo mean | placebo p95 | pass |
| --- | ---: | ---: | ---: | ---: | --- |
| region | 120 | 0.319319 | 0.069487 | 0.077023 | Y |
| temporal | 120 | 0.319319 | 0.128467 | 0.144066 | Y |
| noise | 120 | 0.319319 | -0.075777 | -0.060153 | Y |

## 9. Lag 및 Leakage Sensitivity

| policy | count | leakage rows | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_actual_publication_date | 1101 | 0 | 5.470158 | 5.15084 | 0.319319 |
| L1_observation_plus_1m | 1101 | 0 | 5.470158 | 5.15084 | 0.319319 |
| L2_observation_plus_2m | 1101 | 0 | 5.470158 | 5.13629 | 0.333869 |
| L3_observation_plus_3m | 1101 | 0 | 5.470158 | 5.119775 | 0.350383 |
| latest_source_leakage_benchmark | 1101 | 0 | 5.470158 | 5.119568 | 0.35059 |

## 10. Missingness Stress

| scenario | affected sido | count | delta +good | base delta |
| --- | --- | ---: | ---: | ---: |
| random_5pct |  | 1101 | 0.307282 | 0.319319 |
| random_10pct |  | 1101 | 0.222827 | 0.319319 |
| latest_eligible_month_missing |  | 1101 | 0.0 | 0.319319 |
| one_sido_missing_worst10 | 경기도 | 1101 | 0.183075 | 0.319319 |
| one_sido_missing_worst10 | 서울특별시 | 1101 | 0.198112 | 0.319319 |
| one_sido_missing_worst10 | 전라남도 | 1101 | 0.273069 | 0.319319 |
| one_sido_missing_worst10 | 부산광역시 | 1101 | 0.276434 | 0.319319 |
| one_sido_missing_worst10 | 인천광역시 | 1101 | 0.281272 | 0.319319 |
| one_sido_missing_worst10 | 경상남도 | 1101 | 0.287699 | 0.319319 |
| one_sido_missing_worst10 | 경상북도 | 1101 | 0.290048 | 0.319319 |
| one_sido_missing_worst10 | 전북특별자치도 | 1101 | 0.291909 | 0.319319 |
| one_sido_missing_worst10 | 울산광역시 | 1101 | 0.293334 | 0.319319 |
| one_sido_missing_worst10 | 광주광역시 | 1101 | 0.300086 | 0.319319 |

## 11. Large Observation Removal

| metric | removed top % | removed rows | remaining | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| actual_scale | 1 | 11 | 1090 | 5.628664 | 5.261829 | 0.366835 |
| actual_scale | 5 | 55 | 1046 | 5.895977 | 5.50006 | 0.395918 |
| actual_scale | 10 | 110 | 991 | 6.246298 | 5.852386 | 0.393913 |
| electricity_scale | 1 | 11 | 1090 | 5.476955 | 5.112321 | 0.364635 |
| electricity_scale | 5 | 55 | 1046 | 5.758199 | 5.27554 | 0.482659 |
| electricity_scale | 10 | 110 | 991 | 5.994856 | 5.505542 | 0.489314 |

## 12. Material Degradation Audit

- degradation rule: candidate error > global error * 1.1 and absolute error increase > actual * 2%
- rows flagged under primary best candidate: 137
- APE +1pp rows: 203
- APE +5pp rows: 0
- APE +10pp rows: 0

## 13. 운영 해석

전력 feature는 제조업 및 전체 총량에서만 제한적으로 적용하고 전기가스업은 fallback하는 설계가 가장 방어적이다. 다만 bootstrap과 placebo에서 동시에 강한 신호가 확인되지 않으면 운영 채택보다는 다음 actual vintage에서 재확인하는 것이 맞다.

## 14. 다음 단계

1. O1 후보가 다음 official actual 갱신에서도 같은 방향의 개선을 보이는지 confirmatory test를 수행한다.
2. C00과 all 각각에 별도 alpha를 두는 산업별 alpha 정책을 비교한다.
3. 전력 외 feature를 하나 이상 추가해 placebo 대비 설명력이 독립적으로 유지되는지 확인한다.

## 15. 산출물

- `data/processed/electricity_guardrail_candidates.csv`
- `data/processed/electricity_bootstrap_results.csv`
- `data/processed/electricity_loso_results.csv`
- `data/processed/electricity_placebo_results.csv`
- `data/processed/electricity_lag_sensitivity_results.csv`
- `data/processed/electricity_missingness_results.csv`
- `data/processed/electricity_material_degradation_audit.csv`

모든 CSV는 `kosis_common.write_csv`를 통해 CP949로 저장했다.

## 16. Gate 판단표

| gate | result | note |
| --- | --- | --- |
| vintage leakage | PASS | O1 primary leakage row count is 0 |
| pooled WMAPE improvement | PASS | best delta is 0.319318 |
| bootstrap probability | PASS | pooled P(improve) is 0.999 |
| placebo superiority | PASS | 3/3 placebo families pass p95 |
| material degradation | WATCH | 137 rows flagged |
| industry consistency | WATCH | C00 worsens while all-sector total improves |

## 17. 채택 보류 사유

전체 WMAPE와 bootstrap 신호는 양호하지만, C00 단독에서는 global reference보다 나빠진다. 이는 전력 feature가 제조업 하위 구조를 직접 설명한다기보다 시군구 총량 또는 규모 보정에 더 강하게 작동한다는 뜻이다. 따라서 현재 후보는 운영 채택이 아니라 refinement 후보로 유지한다.

## 18. 데이터 유출 방지 확인

2022년 평가는 2021년 학습 및 2021년 내부 시도 CV로 alpha를 고르고, 2023년 평가는 2021년 학습에서 2022년 validation으로 alpha를 고른 뒤 2021-2022년으로 재학습해 2023년에 적용했다. O1 feature는 해당 연도 3월 말 공표 완료 vintage만 선택한다.

## 19. 구현 메모

실험은 `scripts/run_electricity_guardrail_robustness.py`에서 수행하며, 기존 `run_electricity_vintage_dry_run.py`의 vintage selector, target loader, panel joiner를 재사용한다. `run_electricity_vintage_dry_run.py`에는 lag sensitivity 중 발견된 음수 로그 방지를 위해 로그 변환용 feature에만 0 하한을 적용했다.

## 20. 최종 운영 권고

`P4_trainalpha_B6_relative_rel5_S1`을 다음 confirmatory round의 1순위 후보로 고정한다. 다만 산업별로는 `all`에만 명확한 개선이 있고 `C00`은 악화되므로, 다음 실험은 `all-only`, `C00 별도 alpha`, `C00 no-correction gate`를 같은 vintage-aware 절차로 비교해야 한다.
