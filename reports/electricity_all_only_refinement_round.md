# 전력 Feature All-only Refinement Round

## 1. 실행 요약

- final decision: `all_only_shadow_candidate_retained_but_not_frozen`
- selected shadow candidate: `R2_all_only_trainalpha_B6_rel5`
- WMAPE delta, positive is good: 0.090573
- relative improvement: 1.655762%
- material degradation count: 0
- policy manifest: `data/processed/electricity_shadow_policy_manifest.json`

이번 라운드는 2022-2023 개발 actual에서 후보 확장을 종료하기 위한 정제 실험이다. 전력 feature는 `all` 총량에만 적용하고 `C00`, `D00`은 global fallback하는 방향을 중심으로 검증했다.

## 2. R0~R3 정책 비교

| policy | count | WMAPE | global WMAPE | delta +good | rel improve % | macro WMAPE | median APE | p90 APE | material deg | fallback rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R0_global_reference | 1101 | 5.470158 | 5.470158 | 0.0 | 0.0 | 5.343632 | 5.897335 | 30.216904 | 0 | 0.0 |
| R1_reproduce_P4_C00_all | 1101 | 5.186461 | 5.470158 | 0.283697 | 5.186276 | 4.993464 | 5.749348 | 30.327516 | 0 | 0.316985 |
| R2_all_only_trainalpha_B6_rel5 | 1101 | 5.379586 | 5.470158 | 0.090573 | 1.655762 | 5.151703 | 5.952815 | 30.216904 | 0 | 0.658492 |
| R3_all_only_conservative_B6_rel5 | 1101 | 5.397613 | 5.470158 | 0.072545 | 1.326202 | 5.19754 | 5.993558 | 30.216904 | 0 | 0.658492 |
| R3b_all_only_conservative_B4_rel5 | 1101 | 5.369693 | 5.470158 | 0.100466 | 1.836613 | 5.180697 | 5.892453 | 30.216904 | 0 | 0.658492 |

## 3. 연도/산업/지역별 결과

| grouping | policy | key | count | WMAPE | global WMAPE | delta +good |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| target_year | R0_global_reference | 2022 | 671 | 5.849244 | 5.849244 | 0.0 |
| target_year | R0_global_reference | 2023 | 430 | 4.938687 | 4.938687 | 0.0 |
| target_year | R1_reproduce_P4_C00_all | 2022 | 671 | 5.463951 | 5.849244 | 0.385293 |
| target_year | R1_reproduce_P4_C00_all | 2023 | 430 | 4.797425 | 4.938687 | 0.141263 |
| target_year | R2_all_only_trainalpha_B6_rel5 | 2022 | 671 | 5.53633 | 5.849244 | 0.312914 |
| target_year | R2_all_only_trainalpha_B6_rel5 | 2023 | 430 | 5.159833 | 4.938687 | -0.221146 |
| target_year | R3_all_only_conservative_B6_rel5 | 2022 | 671 | 5.64256 | 5.849244 | 0.206684 |
| target_year | R3_all_only_conservative_B6_rel5 | 2023 | 430 | 5.054202 | 4.938687 | -0.115514 |
| target_year | R3b_all_only_conservative_B4_rel5 | 2022 | 671 | 5.621908 | 5.849244 | 0.227336 |
| target_year | R3b_all_only_conservative_B4_rel5 | 2023 | 430 | 5.016091 | 4.938687 | -0.077404 |
| sector_code | R0_global_reference | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | R0_global_reference | D00 | 349 | 18.558809 | 18.558809 | 0.0 |
| sector_code | R0_global_reference | all | 376 | 4.995672 | 4.995672 | 0.0 |
| sector_code | R1_reproduce_P4_C00_all | C00 | 376 | 5.993862 | 5.817659 | -0.176202 |
| sector_code | R1_reproduce_P4_C00_all | D00 | 349 | 18.558809 | 18.558809 | 0.0 |
| sector_code | R1_reproduce_P4_C00_all | all | 376 | 4.509388 | 4.995672 | 0.486284 |
| sector_code | R2_all_only_trainalpha_B6_rel5 | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | R2_all_only_trainalpha_B6_rel5 | D00 | 349 | 18.558809 | 18.558809 | 0.0 |
| sector_code | R2_all_only_trainalpha_B6_rel5 | all | 376 | 4.864335 | 4.995672 | 0.131337 |
| sector_code | R3_all_only_conservative_B6_rel5 | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | R3_all_only_conservative_B6_rel5 | D00 | 349 | 18.558809 | 18.558809 | 0.0 |
| sector_code | R3_all_only_conservative_B6_rel5 | all | 376 | 4.890476 | 4.995672 | 0.105196 |
| sector_code | R3b_all_only_conservative_B4_rel5 | C00 | 376 | 5.817659 | 5.817659 | 0.0 |
| sector_code | R3b_all_only_conservative_B4_rel5 | D00 | 349 | 18.558809 | 18.558809 | 0.0 |
| sector_code | R3b_all_only_conservative_B4_rel5 | all | 376 | 4.84999 | 4.995672 | 0.145682 |
| source_region | R0_global_reference | 강원특별자치도 | 54 | 6.731901 | 6.731901 | 0.0 |
| source_region | R0_global_reference | 경기도 | 164 | 5.581454 | 5.581454 | 0.0 |
| source_region | R0_global_reference | 경상남도 | 54 | 2.829606 | 2.829606 | 0.0 |
| source_region | R0_global_reference | 경상북도 | 138 | 5.025512 | 5.025512 | 0.0 |
| source_region | R0_global_reference | 광주광역시 | 30 | 6.217865 | 6.217865 | 0.0 |
| source_region | R0_global_reference | 대구광역시 | 24 | 4.918174 | 4.918174 | 0.0 |
| source_region | R0_global_reference | 대전광역시 | 26 | 5.829128 | 5.829128 | 0.0 |
| source_region | R0_global_reference | 부산광역시 | 48 | 8.061561 | 8.061561 | 0.0 |
| source_region | R0_global_reference | 서울특별시 | 150 | 6.951748 | 6.951748 | 0.0 |
| source_region | R0_global_reference | 울산광역시 | 15 | 6.212278 | 6.212278 | 0.0 |
| source_region | R0_global_reference | 인천광역시 | 60 | 5.432148 | 5.432148 | 0.0 |
| source_region | R0_global_reference | 전라남도 | 132 | 6.242793 | 6.242793 | 0.0 |
| source_region | R0_global_reference | 전북특별자치도 | 83 | 4.123662 | 4.123662 | 0.0 |
| source_region | R0_global_reference | 제주특별자치도 | 12 | 3.869796 | 3.869796 | 0.0 |
| source_region | R0_global_reference | 충청남도 | 45 | 4.120658 | 4.120658 | 0.0 |
| source_region | R0_global_reference | 충청북도 | 66 | 3.349833 | 3.349833 | 0.0 |
| source_region | R1_reproduce_P4_C00_all | 강원특별자치도 | 54 | 5.367453 | 6.731901 | 1.364449 |
| source_region | R1_reproduce_P4_C00_all | 경기도 | 164 | 5.222244 | 5.581454 | 0.35921 |
| source_region | R1_reproduce_P4_C00_all | 경상남도 | 54 | 2.237094 | 2.829606 | 0.592512 |
| source_region | R1_reproduce_P4_C00_all | 경상북도 | 138 | 4.897738 | 5.025512 | 0.127774 |
| source_region | R1_reproduce_P4_C00_all | 광주광역시 | 30 | 5.795083 | 6.217865 | 0.422782 |
| source_region | R1_reproduce_P4_C00_all | 대구광역시 | 24 | 5.320468 | 4.918174 | -0.402294 |
| source_region | R1_reproduce_P4_C00_all | 대전광역시 | 26 | 5.320794 | 5.829128 | 0.508334 |
| source_region | R1_reproduce_P4_C00_all | 부산광역시 | 48 | 6.37442 | 8.061561 | 1.687141 |
| source_region | R1_reproduce_P4_C00_all | 서울특별시 | 150 | 6.396159 | 6.951748 | 0.555589 |
| source_region | R1_reproduce_P4_C00_all | 울산광역시 | 15 | 6.891363 | 6.212278 | -0.679085 |
| source_region | R1_reproduce_P4_C00_all | 인천광역시 | 60 | 5.155111 | 5.432148 | 0.277036 |
| source_region | R1_reproduce_P4_C00_all | 전라남도 | 132 | 5.948684 | 6.242793 | 0.294108 |
| source_region | R1_reproduce_P4_C00_all | 전북특별자치도 | 83 | 3.519836 | 4.123662 | 0.603827 |
| source_region | R1_reproduce_P4_C00_all | 제주특별자치도 | 12 | 2.836317 | 3.869796 | 1.033479 |
| source_region | R1_reproduce_P4_C00_all | 충청남도 | 45 | 4.675844 | 4.120658 | -0.555186 |
| source_region | R1_reproduce_P4_C00_all | 충청북도 | 66 | 3.936814 | 3.349833 | -0.586982 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 강원특별자치도 | 54 | 5.810159 | 6.731901 | 0.921742 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 경기도 | 164 | 5.592299 | 5.581454 | -0.010845 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 경상남도 | 54 | 2.098611 | 2.829606 | 0.730995 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 경상북도 | 138 | 5.111422 | 5.025512 | -0.08591 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 광주광역시 | 30 | 5.634957 | 6.217865 | 0.582908 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 대구광역시 | 24 | 5.221742 | 4.918174 | -0.303568 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 대전광역시 | 26 | 5.957133 | 5.829128 | -0.128006 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 부산광역시 | 48 | 7.278703 | 8.061561 | 0.782858 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 서울특별시 | 150 | 6.59613 | 6.951748 | 0.355618 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 울산광역시 | 15 | 6.456953 | 6.212278 | -0.244675 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 인천광역시 | 60 | 5.654194 | 5.432148 | -0.222046 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 전라남도 | 132 | 6.254487 | 6.242793 | -0.011695 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 전북특별자치도 | 83 | 3.532859 | 4.123662 | 0.590803 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 제주특별자치도 | 12 | 3.51879 | 3.869796 | 0.351007 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 충청남도 | 45 | 4.349763 | 4.120658 | -0.229105 |
| source_region | R2_all_only_trainalpha_B6_rel5 | 충청북도 | 66 | 3.35904 | 3.349833 | -0.009208 |
| source_region | R3_all_only_conservative_B6_rel5 | 강원특별자치도 | 54 | 6.127402 | 6.731901 | 0.604499 |
| source_region | R3_all_only_conservative_B6_rel5 | 경기도 | 164 | 5.577621 | 5.581454 | 0.003833 |
| source_region | R3_all_only_conservative_B6_rel5 | 경상남도 | 54 | 2.370938 | 2.829606 | 0.458668 |
| source_region | R3_all_only_conservative_B6_rel5 | 경상북도 | 138 | 5.037103 | 5.025512 | -0.011591 |
| source_region | R3_all_only_conservative_B6_rel5 | 광주광역시 | 30 | 5.838436 | 6.217865 | 0.379429 |
| source_region | R3_all_only_conservative_B6_rel5 | 대구광역시 | 24 | 5.107904 | 4.918174 | -0.18973 |
| source_region | R3_all_only_conservative_B6_rel5 | 대전광역시 | 26 | 5.909131 | 5.829128 | -0.080003 |
| source_region | R3_all_only_conservative_B6_rel5 | 부산광역시 | 48 | 7.572275 | 8.061561 | 0.489286 |
| source_region | R3_all_only_conservative_B6_rel5 | 서울특별시 | 150 | 6.719774 | 6.951748 | 0.231974 |
| source_region | R3_all_only_conservative_B6_rel5 | 울산광역시 | 15 | 6.3652 | 6.212278 | -0.152922 |
| source_region | R3_all_only_conservative_B6_rel5 | 인천광역시 | 60 | 5.55347 | 5.432148 | -0.121323 |
| source_region | R3_all_only_conservative_B6_rel5 | 전라남도 | 132 | 6.21815 | 6.242793 | 0.024643 |
| source_region | R3_all_only_conservative_B6_rel5 | 전북특별자치도 | 83 | 3.713305 | 4.123662 | 0.410357 |
| source_region | R3_all_only_conservative_B6_rel5 | 제주특별자치도 | 12 | 3.445445 | 3.869796 | 0.424352 |
| source_region | R3_all_only_conservative_B6_rel5 | 충청남도 | 45 | 4.263849 | 4.120658 | -0.143191 |
| source_region | R3_all_only_conservative_B6_rel5 | 충청북도 | 66 | 3.340632 | 3.349833 | 0.009201 |
| source_region | R3b_all_only_conservative_B4_rel5 | 강원특별자치도 | 54 | 6.074725 | 6.731901 | 0.657177 |
| source_region | R3b_all_only_conservative_B4_rel5 | 경기도 | 164 | 5.53828 | 5.581454 | 0.043174 |
| source_region | R3b_all_only_conservative_B4_rel5 | 경상남도 | 54 | 2.408284 | 2.829606 | 0.421322 |
| source_region | R3b_all_only_conservative_B4_rel5 | 경상북도 | 138 | 5.021263 | 5.025512 | 0.004249 |
| source_region | R3b_all_only_conservative_B4_rel5 | 광주광역시 | 30 | 5.887839 | 6.217865 | 0.330026 |
| source_region | R3b_all_only_conservative_B4_rel5 | 대구광역시 | 24 | 5.060074 | 4.918174 | -0.1419 |
| source_region | R3b_all_only_conservative_B4_rel5 | 대전광역시 | 26 | 5.843125 | 5.829128 | -0.013997 |
| source_region | R3b_all_only_conservative_B4_rel5 | 부산광역시 | 48 | 7.491035 | 8.061561 | 0.570526 |
| source_region | R3b_all_only_conservative_B4_rel5 | 서울특별시 | 150 | 6.668209 | 6.951748 | 0.283539 |
| source_region | R3b_all_only_conservative_B4_rel5 | 울산광역시 | 15 | 6.36979 | 6.212278 | -0.157512 |
| source_region | R3b_all_only_conservative_B4_rel5 | 인천광역시 | 60 | 5.516698 | 5.432148 | -0.084551 |
| source_region | R3b_all_only_conservative_B4_rel5 | 전라남도 | 132 | 6.197563 | 6.242793 | 0.04523 |
| source_region | R3b_all_only_conservative_B4_rel5 | 전북특별자치도 | 83 | 3.743142 | 4.123662 | 0.38052 |
| source_region | R3b_all_only_conservative_B4_rel5 | 제주특별자치도 | 12 | 3.504727 | 3.869796 | 0.365069 |
| source_region | R3b_all_only_conservative_B4_rel5 | 충청남도 | 45 | 4.220807 | 4.120658 | -0.100148 |
| source_region | R3b_all_only_conservative_B4_rel5 | 충청북도 | 66 | 3.345587 | 3.349833 | 0.004245 |

## 4. Alpha 및 Ridge Lambda 선택

| policy | test_year | alpha | validation WMAPE | validation score | degradation rate | count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R1_reproduce_P4_C00_all | 2022 | 0.0 | 5.45301 | 5.45301 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.05 | 5.34808 | 5.34808 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.1 | 5.244962 | 5.244962 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.15 | 5.145258 | 5.145258 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.2 | 5.04896 | 5.04896 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.25 | 4.956555 | 4.956555 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.3 | 4.873255 | 4.873255 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.4 | 4.72346 | 4.72346 | 0.0 | 672 |
| R1_reproduce_P4_C00_all | 2022 | 0.5 | 4.599496 | 7.687294 | 0.123512 | 672 |
| R1_reproduce_P4_C00_all | 2023 | 0.0 | 5.849244 | 5.849244 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.05 | 5.782361 | 5.782361 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.1 | 5.723115 | 5.723115 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.15 | 5.668282 | 5.668282 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.2 | 5.615604 | 5.615604 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.25 | 5.5691 | 5.5691 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.3 | 5.529028 | 5.529028 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.4 | 5.463951 | 5.463951 | 0.0 | 671 |
| R1_reproduce_P4_C00_all | 2023 | 0.5 | 5.426617 | 10.530939 | 0.204173 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.0 | 5.45301 | 5.45301 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.05 | 5.400249 | 5.400249 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.1 | 5.348158 | 5.348158 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.15 | 5.297932 | 5.297932 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.2 | 5.248425 | 5.248425 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.25 | 5.199543 | 5.199543 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.3 | 5.152035 | 5.152035 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.4 | 5.075787 | 5.075787 | 0.0 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2022 | 0.5 | 5.012664 | 5.496295 | 0.019345 | 672 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.0 | 5.849244 | 5.849244 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.05 | 5.805551 | 5.805551 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.1 | 5.763114 | 5.763114 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.15 | 5.722474 | 5.722474 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.2 | 5.682353 | 5.682353 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.25 | 5.64256 | 5.64256 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.3 | 5.603862 | 5.603862 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.4 | 5.53633 | 5.53633 | 0.0 | 671 |
| R2_all_only_trainalpha_B6_rel5 | 2023 | 0.5 | 5.484383 | 5.856961 | 0.014903 | 671 |
| R3_all_only_conservative_B6_rel5 | 2022 | 0.1 | 5.348158 | 5.348158 | 0.0 | 672 |
| R3_all_only_conservative_B6_rel5 | 2022 | 0.15 | 5.297932 | 5.297932 | 0.0 | 672 |
| R3_all_only_conservative_B6_rel5 | 2022 | 0.25 | 5.199543 | 5.199543 | 0.0 | 672 |
| R3_all_only_conservative_B6_rel5 | 2023 | 0.1 | 5.763114 | 5.763114 | 0.0 | 671 |
| R3_all_only_conservative_B6_rel5 | 2023 | 0.15 | 5.722474 | 5.722474 | 0.0 | 671 |
| R3_all_only_conservative_B6_rel5 | 2023 | 0.25 | 5.64256 | 5.64256 | 0.0 | 671 |
| R3b_all_only_conservative_B4_rel5 | 2022 | 0.1 | 5.353521 | 5.353521 | 0.0 | 672 |
| R3b_all_only_conservative_B4_rel5 | 2022 | 0.15 | 5.305906 | 5.305906 | 0.0 | 672 |
| R3b_all_only_conservative_B4_rel5 | 2022 | 0.25 | 5.212233 | 5.212233 | 0.0 | 672 |
| R3b_all_only_conservative_B4_rel5 | 2023 | 0.1 | 5.754354 | 5.754354 | 0.0 | 671 |
| R3b_all_only_conservative_B4_rel5 | 2023 | 0.15 | 5.709014 | 5.709014 | 0.0 | 671 |
| R3b_all_only_conservative_B4_rel5 | 2023 | 0.25 | 5.621908 | 5.621908 | 0.0 | 671 |

## 5. 일반 Bootstrap

| policy | iterations | mean delta | CI 2.5 | CI 97.5 | P(improve) |
| --- | ---: | ---: | ---: | ---: | ---: |
| R1_reproduce_P4_C00_all | 2000 | 0.285937 | 0.123132 | 0.458478 | 1.0 |
| R2_all_only_trainalpha_B6_rel5 | 2000 | 0.097847 | -0.069947 | 0.266212 | 0.868 |
| R3_all_only_conservative_B6_rel5 | 2000 | 0.076172 | -0.030341 | 0.180308 | 0.921 |
| R3b_all_only_conservative_B4_rel5 | 2000 | 0.104694 | 0.011884 | 0.203314 | 0.988 |

## 6. Selection-aware Bootstrap

| type | selected policy/alpha | count | frequency | mean improvement | CI 2.5 | CI 97.5 | P(improve) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| selection_aware_delta |  |  |  | 0.083125 | -0.100668 | 0.255035 | 0.789 |
| selected_policy_frequency | R2_all_only_trainalpha_B6_rel5 | 743 | 0.743 |  |  |  |  |
| selected_policy_frequency | R3_all_only_conservative_B6_rel5 | 257 | 0.257 |  |  |  |  |
| selected_alpha_frequency | 0.4 | 743 | 0.743 |  |  |  |  |
| selected_alpha_frequency | 0.25 | 257 | 0.257 |  |  |  |  |

## 7. Coefficient 안정성

| policy | feature | n | mean | std | positive rate | negative rate | flag |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| R1_reproduce_P4_C00_all | commercial_share_trailing12 | 2 | -0.00107193 | 0.00052914 | 0.0 | 1.0 | stable |
| R1_reproduce_P4_C00_all | eligible_observation_count | 2 | 0.00539639 | 0.00539639 | 0.5 | 0.0 | unstable |
| R1_reproduce_P4_C00_all | industrial_share_of_sido | 2 | 0.0 | 0.0 | 0.0 | 0.0 | unstable |
| R1_reproduce_P4_C00_all | industrial_share_trailing12 | 2 | 0.00410958 | 1.119e-05 | 1.0 | 0.0 | stable |
| R1_reproduce_P4_C00_all | log_industrial_trailing12_sum | 2 | 0.00517647 | 0.000442 | 1.0 | 0.0 | stable |
| R1_reproduce_P4_C00_all | log_total_trailing12_sum | 2 | 0.00404491 | 0.00066831 | 1.0 | 0.0 | stable |
| R2_all_only_trainalpha_B6_rel5 | commercial_share_trailing12 | 2 | 0.01012425 | 0.00738576 | 1.0 | 0.0 | stable |
| R2_all_only_trainalpha_B6_rel5 | eligible_observation_count | 2 | -0.00156704 | 0.00156704 | 0.0 | 0.5 | unstable |
| R2_all_only_trainalpha_B6_rel5 | industrial_share_of_sido | 2 | 0.0 | 0.0 | 0.0 | 0.0 | unstable |
| R2_all_only_trainalpha_B6_rel5 | industrial_share_trailing12 | 2 | 0.01961139 | 0.00821524 | 1.0 | 0.0 | stable |
| R2_all_only_trainalpha_B6_rel5 | log_industrial_trailing12_sum | 2 | -0.00782057 | 0.01292129 | 0.5 | 0.5 | unstable |
| R2_all_only_trainalpha_B6_rel5 | log_total_trailing12_sum | 2 | 0.00285984 | 0.0076289 | 0.5 | 0.5 | unstable |
| R3_all_only_conservative_B6_rel5 | commercial_share_trailing12 | 2 | 0.01012425 | 0.00738576 | 1.0 | 0.0 | stable |
| R3_all_only_conservative_B6_rel5 | eligible_observation_count | 2 | -0.00156704 | 0.00156704 | 0.0 | 0.5 | unstable |
| R3_all_only_conservative_B6_rel5 | industrial_share_of_sido | 2 | 0.0 | 0.0 | 0.0 | 0.0 | unstable |
| R3_all_only_conservative_B6_rel5 | industrial_share_trailing12 | 2 | 0.01961139 | 0.00821524 | 1.0 | 0.0 | stable |
| R3_all_only_conservative_B6_rel5 | log_industrial_trailing12_sum | 2 | -0.00782057 | 0.01292129 | 0.5 | 0.5 | unstable |
| R3_all_only_conservative_B6_rel5 | log_total_trailing12_sum | 2 | 0.00285984 | 0.0076289 | 0.5 | 0.5 | unstable |
| R3b_all_only_conservative_B4_rel5 | industrial_share_of_sido | 2 | 0.0 | 0.0 | 0.0 | 0.0 | unstable |
| R3b_all_only_conservative_B4_rel5 | industrial_share_trailing12 | 2 | 0.01215332 | 0.00256254 | 1.0 | 0.0 | stable |
| R3b_all_only_conservative_B4_rel5 | log_industrial_trailing12_sum | 2 | -0.01188153 | 0.01592615 | 0.5 | 0.5 | unstable |
| R3b_all_only_conservative_B4_rel5 | log_total_trailing12_sum | 2 | 0.00808674 | 0.01180971 | 0.5 | 0.5 | unstable |

## 8. Missingness

| scenario | coverage threshold | count | base delta | delta +good |
| --- | ---: | ---: | ---: | ---: |
| M1_hard_fallback_latest_month_missing |  | 1101 | 0.090573 | 0.0 |
| M2_prior_vintage_recalculation | 0.75 | 1101 | 0.090573 | 0.090573 |
| M2_prior_vintage_recalculation | 0.9 | 1101 | 0.090573 | 0.090573 |
| M2_prior_vintage_recalculation | 1.0 | 1101 | 0.090573 | 0.0 |

## 9. Placebo

| placebo | iterations | real delta | placebo mean | placebo p95 | pass |
| --- | ---: | ---: | ---: | ---: | --- |
| region | 120 | 0.090573 | 0.041016 | 0.074246 | Y |
| temporal | 120 | 0.090573 | 0.116302 | 0.129663 | N |
| noise | 120 | 0.090573 | 0.074012 | 0.111682 | N |

## 10. Lag Sensitivity

| lag | count | leakage rows | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: | ---: |
| L0_actual_publication_date | 1101 | 0 | 5.470158 | 5.379586 | 0.090573 |
| L1_observation_plus_1m | 1101 | 0 | 5.470158 | 5.379586 | 0.090573 |
| L2_observation_plus_2m | 1101 | 0 | 5.470158 | 5.382409 | 0.08775 |
| L3_observation_plus_3m | 1101 | 0 | 5.470158 | 5.385041 | 0.085117 |

## 11. Leave-one-sido-out

| heldout | count | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: |
| 강원특별자치도 | 54 | 6.731901 | 5.978791 | 0.75311 |
| 경기도 | 164 | 5.581454 | 5.546041 | 0.035413 |
| 경상남도 | 54 | 2.829606 | 2.374502 | 0.455104 |
| 경상북도 | 138 | 5.025512 | 5.061935 | -0.036423 |
| 광주광역시 | 30 | 6.217865 | 5.846699 | 0.371167 |
| 대구광역시 | 24 | 4.918174 | 4.972967 | -0.054793 |
| 대전광역시 | 26 | 5.829128 | 5.720778 | 0.10835 |
| 부산광역시 | 48 | 8.061561 | 7.420921 | 0.64064 |
| 서울특별시 | 150 | 6.951748 | 6.521124 | 0.430624 |
| 울산광역시 | 15 | 6.212278 | 6.396461 | -0.184183 |
| 인천광역시 | 60 | 5.432148 | 5.579347 | -0.1472 |
| 전라남도 | 132 | 6.242793 | 6.21903 | 0.023763 |
| 전북특별자치도 | 83 | 4.123662 | 3.747961 | 0.375702 |
| 제주특별자치도 | 12 | 3.869796 | 3.305784 | 0.564012 |
| 충청남도 | 45 | 4.120658 | 4.262695 | -0.142037 |
| 충청북도 | 66 | 3.349833 | 3.323356 | 0.026477 |

## 12. Large Observation Removal

| metric | removed top % | removed rows | global WMAPE | candidate WMAPE | delta +good |
| --- | ---: | ---: | ---: | ---: | ---: |
| actual_scale | 1 | 11 | 5.628664 | 5.456571 | 0.172093 |
| actual_scale | 5 | 55 | 5.895977 | 5.686946 | 0.209031 |
| actual_scale | 10 | 110 | 6.246298 | 6.019661 | 0.226638 |
| electricity_scale | 1 | 11 | 5.476955 | 5.304463 | 0.172492 |
| electricity_scale | 5 | 55 | 5.758199 | 5.516032 | 0.242167 |
| electricity_scale | 10 | 110 | 5.994856 | 5.749186 | 0.24567 |

## 13. Material Degradation

- selected candidate material degradation: 0
- selected candidate APE +5pp: 0
- selected candidate APE +10pp: 0
- detailed row audit: `data/processed/electricity_all_only_degradation.csv` (1101 rows)

## 14. Gate 판단

| gate | result | note |
| --- | --- | --- |
| primary WMAPE | PASS | delta 0.090573 |
| macro WMAPE | PASS | candidate 5.151703 vs global 5.343632 |
| material degradation <=95 | PASS | 0 |
| severe degradation | PASS | +5pp 0, +10pp 0 |
| placebo | WATCH | real > p95 required |

## 15. 최종 Decision

`all_only_shadow_candidate_retained_but_not_frozen`

2022-2023 개발 데이터에서 전력 feature는 all-only shadow 후보로 유지한다. 다만 2023년 및 placebo gate가 약하므로 운영 정책으로 동결하지 않는다. 이 결과를 바탕으로 같은 개발 actual에서 신규 후보를 추가 탐색하기보다는 다음 미사용 official actual에서 confirmatory test를 수행한다.

## 16. Confirmatory 정책

- application: all only
- fallback: C00 global, D00 global, missing feature global
- origin: O1
- feature bundle: B6 full without change
- alpha selection: training validation multiobjective score
- clipping: relative 5%
- confirmatory period: 2024 이후 또는 정책 동결 이후 최초 확보되는 미사용 official actual
