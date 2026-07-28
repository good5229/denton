# 전국 시군구 기반 분기누적 GRDP/GDP 집계검증

생성시각: 2026-07-28T21:21:18+09:00

## 목적

경기도·경북에서 수행한 `시군구×업종 하위 추정 → 시도 분기 GRDP actual 집계검증` 절차를 전국으로 확장했다. BOK RECI 문서의 17개 광역자치단체 기준에 맞춰 세종은 `세종시` 1개 하위단위로 처리했다. 17개 시도의 하위단위·업종 연간 GVA를 분기화하고, 시도별 분기누적/연간환산 WAPE를 계산한 뒤, 17개 시도 합계를 전국 공식 분기 GDP/GRDP 경계와 비교했다.

## 핵심 원칙

| 원칙 | 적용 |
| --- | --- |
| 목표분기 시도 actual 배분비 사용 금지 | 사용하지 않음 |
| 하위 추정값의 상위 집계검증 | 시군구/단층시→시도, 17개 시도→전국 |
| GVA와 GRDP 구분 | 시군구 업종 GVA + 별도 기타산업·순생산물세 bridge |
| 세종 처리 | BOK 17개 광역 기준 반영. `세종특별자치시→세종시` 1개 하위단위로 보존 |

## 검증 감사

| 검사 | 값 | 판정 |
| --- | --- | --- |
| covered_provinces | 17 | 17; Sejong handled as one-tier pseudo sigungu |
| sigungu_with_2023_local_source | 149 | 2023 local source coverage, not total national municipalities |
| city_quarter_prediction_rows | 119,080 | information |
| province_total_validation_missing_actual | 0 | 0 |
| activity_validation_missing_actual | 0 | 0 |
| national_validation_missing_actual | 0 | 0 |

## 기준값 사용 감사

| 항목 | 내용 |
| --- | --- |
| 2023년 시군구 원천 부재 시도 | 부산, 대구, 울산, 강원, 충남, 경남 |
| 처리 | 엄격 속보형은 직전 예측 연간합을 이어 쓰고, 정밀형은 직전연도 시도 공식 업종합으로 구조를 보정 |
| 주의 | 정밀형은 사후 또는 충분한 공표시차 이후 활용 지표이며, Q+1개월 엄격 속보 지표로 해석하지 않음 |

| 트랙 | 연도 | 기준값출처 | 예측행 |
| --- | --- | --- | --- |
| prior_year_province_anchor | 2021 | official_sigungu_annual_2020 | 11,908 |
| prior_year_province_anchor | 2022 | official_sigungu_annual_2021 | 11,908 |
| prior_year_province_anchor | 2023 | official_sigungu_annual_2022 | 11,908 |
| prior_year_province_anchor | 2024 | lagged_basis_2023_scaled_to_prior_year_official_sido_activity | 11,908 |
| prior_year_province_anchor | 2025 | lagged_basis_2024_scaled_to_prior_year_official_sido_activity | 11,908 |
| recursive_no_target_actual | 2021 | official_sigungu_annual_2020 | 11,908 |
| recursive_no_target_actual | 2022 | official_sigungu_annual_2021 | 11,908 |
| recursive_no_target_actual | 2023 | official_sigungu_annual_2022 | 11,908 |
| recursive_no_target_actual | 2024 | recursive_predicted_sigungu_2023 | 11,908 |
| recursive_no_target_actual | 2025 | recursive_predicted_sigungu_2024 | 11,908 |

## 모의 운영시점별 전국 17개 시도 전체 요약

본 표는 최신 공표 빈티지 기준의 사후 백테스트다. `1분기+1개월` 등은 사용 분기 수를 구분하기 위한 운영 화면 명칭이며, 과거 각 시점의 원천 빈티지를 완전 복원한 실시간 성과가 아니다.

| 트랙 | 사용분기수 | 모의운영시점 | 검증행 | 연간환산WAPE_pct | 연간환산최대오차율_pct | 누적분기WAPE_pct | 누적분기최대오차율_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 1 | 1분기+1개월 | 85 | 1.643 | 6.654 | 1.207 | 5.335 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 85 | 1.139 | 5.361 | 1.238 | 5.850 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 85 | 1.054 | 4.749 | 1.126 | 4.439 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 85 | 1.073 | 4.076 | 1.073 | 4.076 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 85 | 1.894 | 9.384 | 1.462 | 7.984 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 85 | 1.402 | 8.073 | 1.564 | 6.932 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 85 | 1.304 | 7.453 | 1.382 | 6.446 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 85 | 1.321 | 6.763 | 1.321 | 6.763 |

## 전국 GDP 경계 검증: 17개 시도 합계 vs 전국

전국 계절비중을 사용하기 때문에 전국 경계 WAPE는 구조적으로 작아질 수 있다. 따라서 이 표는 시군구·시도 추정값의 외부 일관성 참고지표이며, 시도별·업종별 예측력이 모두 높다는 뜻은 아니다.

| 트랙 | 연도 | 분기수 | 공식전국GDP_억원 | 17개시도예측합_억원 | 절대오차합_억원 | 전국경계WAPE_pct |
| --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 2021 | 4 | 21,559,933.590 | 21,559,933.680 | 0.090 | 0.000 |
| prior_year_province_anchor | 2022 | 4 | 22,149,106.820 | 22,140,190.657 | 10,114.934 | 0.046 |
| prior_year_province_anchor | 2023 | 4 | 22,501,383.510 | 22,485,852.032 | 15,531.478 | 0.069 |
| prior_year_province_anchor | 2024 | 4 | 22,953,418.110 | 22,924,254.004 | 29,164.106 | 0.127 |
| prior_year_province_anchor | 2025 | 4 | 23,205,968.860 | 23,195,923.419 | 12,567.163 | 0.054 |
| recursive_no_target_actual | 2021 | 4 | 21,559,933.590 | 21,559,933.680 | 0.090 | 0.000 |
| recursive_no_target_actual | 2022 | 4 | 22,149,106.820 | 22,140,190.657 | 10,114.934 | 0.046 |
| recursive_no_target_actual | 2023 | 4 | 22,501,383.510 | 22,485,852.032 | 15,531.478 | 0.069 |
| recursive_no_target_actual | 2024 | 4 | 22,953,418.110 | 22,954,898.173 | 7,557.769 | 0.033 |
| recursive_no_target_actual | 2025 | 4 | 23,205,968.860 | 23,218,147.763 | 14,528.746 | 0.063 |

## 연간환산 WAPE가 큰 시도·운영시점

| 트랙 | 시도 | 사용분기수 | 모의운영시점 | 연도수 | 연간환산절대오차합_억원 | 연간환산WAPE_pct | 연간환산최대오차율_pct | 누적분기WAPE_pct | 누적분기최대오차율_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 인천 | 1 | 1분기+1개월 | 5 | 197,308.399 | 3.582 | 5.198 | 2.554 | 4.855 |
| recursive_no_target_actual | 울산 | 1 | 1분기+1개월 | 5 | 138,599.088 | 3.544 | 6.122 | 2.946 | 4.908 |
| recursive_no_target_actual | 세종 | 1 | 1분기+1개월 | 5 | 27,278.134 | 3.533 | 5.686 | 1.781 | 5.088 |
| recursive_no_target_actual | 대구 | 1 | 1분기+1개월 | 5 | 113,910.978 | 3.427 | 5.858 | 1.321 | 3.245 |
| recursive_no_target_actual | 울산 | 4 | 공표 후 정밀화 | 5 | 123,902.616 | 3.168 | 4.486 | 3.168 | 4.486 |
| prior_year_province_anchor | 세종 | 1 | 1분기+1개월 | 5 | 24,138.491 | 3.127 | 5.259 | 2.125 | 5.088 |
| recursive_no_target_actual | 울산 | 2 | 1~2분기+1개월 | 5 | 120,501.868 | 3.081 | 5.198 | 4.625 | 5.850 |
| recursive_no_target_actual | 인천 | 2 | 1~2분기+1개월 | 5 | 169,144.531 | 3.070 | 4.591 | 2.703 | 4.809 |
| recursive_no_target_actual | 충북 | 1 | 1분기+1개월 | 5 | 126,206.859 | 3.049 | 9.384 | 3.578 | 7.984 |
| recursive_no_target_actual | 울산 | 3 | 1~3분기+1개월 | 5 | 115,659.408 | 2.958 | 4.680 | 3.586 | 4.539 |
| recursive_no_target_actual | 충북 | 4 | 공표 후 정밀화 | 5 | 121,329.120 | 2.931 | 6.763 | 2.931 | 6.763 |
| recursive_no_target_actual | 인천 | 4 | 공표 후 정밀화 | 5 | 160,314.776 | 2.910 | 4.354 | 2.910 | 4.354 |
| prior_year_province_anchor | 충북 | 1 | 1분기+1개월 | 5 | 117,530.564 | 2.840 | 6.654 | 1.898 | 5.335 |
| recursive_no_target_actual | 인천 | 3 | 1~3분기+1개월 | 5 | 154,646.089 | 2.807 | 4.185 | 2.842 | 4.779 |
| recursive_no_target_actual | 대구 | 3 | 1~3분기+1개월 | 5 | 89,431.853 | 2.690 | 6.030 | 1.989 | 5.279 |
| recursive_no_target_actual | 대구 | 2 | 1~2분기+1개월 | 5 | 88,971.082 | 2.676 | 5.525 | 1.589 | 4.839 |
| recursive_no_target_actual | 충북 | 3 | 1~3분기+1개월 | 5 | 110,637.426 | 2.673 | 7.453 | 3.001 | 6.446 |
| prior_year_province_anchor | 울산 | 1 | 1분기+1개월 | 5 | 103,974.019 | 2.659 | 6.122 | 2.061 | 4.908 |
| recursive_no_target_actual | 충북 | 2 | 1~2분기+1개월 | 5 | 107,479.620 | 2.597 | 8.073 | 2.825 | 6.932 |
| recursive_no_target_actual | 전북 | 2 | 1~2분기+1개월 | 5 | 76,380.335 | 2.596 | 3.647 | 2.347 | 3.501 |
| prior_year_province_anchor | 강원 | 1 | 1분기+1개월 | 5 | 71,258.498 | 2.564 | 5.082 | 3.285 | 4.888 |
| prior_year_province_anchor | 대구 | 1 | 1분기+1개월 | 5 | 84,727.049 | 2.549 | 4.918 | 0.851 | 1.654 |
| recursive_no_target_actual | 전북 | 3 | 1~3분기+1개월 | 5 | 73,704.340 | 2.505 | 3.501 | 2.517 | 3.891 |
| recursive_no_target_actual | 대구 | 4 | 공표 후 정밀화 | 5 | 82,435.724 | 2.480 | 6.086 | 2.480 | 6.086 |
| prior_year_province_anchor | 충북 | 4 | 공표 후 정밀화 | 5 | 98,960.666 | 2.391 | 4.076 | 2.391 | 4.076 |
| prior_year_province_anchor | 충북 | 2 | 1~2분기+1개월 | 5 | 93,557.125 | 2.260 | 5.361 | 2.353 | 4.264 |
| prior_year_province_anchor | 경북 | 2 | 1~2분기+1개월 | 5 | 125,113.066 | 2.125 | 3.368 | 2.099 | 3.719 |
| prior_year_province_anchor | 충북 | 3 | 1~3분기+1개월 | 5 | 87,172.334 | 2.106 | 4.749 | 2.443 | 3.769 |
| prior_year_province_anchor | 인천 | 4 | 공표 후 정밀화 | 5 | 115,084.667 | 2.089 | 4.004 | 2.089 | 4.004 |
| prior_year_province_anchor | 세종 | 2 | 1~2분기+1개월 | 5 | 16,101.543 | 2.086 | 3.723 | 1.440 | 4.158 |
| recursive_no_target_actual | 전북 | 4 | 공표 후 정밀화 | 5 | 61,298.993 | 2.083 | 3.345 | 2.083 | 3.345 |
| prior_year_province_anchor | 인천 | 3 | 1~3분기+1개월 | 5 | 107,949.221 | 1.960 | 4.185 | 2.004 | 4.127 |
| prior_year_province_anchor | 인천 | 2 | 1~2분기+1개월 | 5 | 105,179.441 | 1.909 | 4.591 | 1.679 | 3.918 |
| prior_year_province_anchor | 경북 | 3 | 1~3분기+1개월 | 5 | 110,920.713 | 1.884 | 2.961 | 1.622 | 2.758 |
| prior_year_province_anchor | 울산 | 4 | 공표 후 정밀화 | 5 | 71,052.933 | 1.817 | 3.798 | 1.817 | 3.798 |
| prior_year_province_anchor | 대구 | 3 | 1~3분기+1개월 | 5 | 60,339.142 | 1.815 | 3.416 | 1.124 | 1.822 |
| prior_year_province_anchor | 대구 | 2 | 1~2분기+1개월 | 5 | 59,880.375 | 1.801 | 3.846 | 0.731 | 1.413 |
| prior_year_province_anchor | 전남 | 3 | 1~3분기+1개월 | 5 | 74,468.243 | 1.724 | 3.934 | 1.569 | 2.592 |
| prior_year_province_anchor | 제주 | 4 | 공표 후 정밀화 | 5 | 20,124.395 | 1.708 | 2.807 | 1.708 | 2.807 |
| prior_year_province_anchor | 전남 | 4 | 공표 후 정밀화 | 5 | 69,199.428 | 1.602 | 3.223 | 1.602 | 3.223 |

## 해석

1. 현재 로컬 원천으로는 17개 시도 전체에 대해 하위단위×업종 분기 추정이 가능하다. 세종은 하위 시군구가 없는 단층 지자체이므로 1개 하위단위로 처리한다.
2. 부산·대구·울산·강원·충남·경남은 2023년 시군구 연간 원천이 부재하여 일부 연도는 직전 예측값 또는 직전연도 시도 공식 업종합 보정을 사용했다. 해당 지역의 성과지표는 원천 공백 보정 효과를 포함한다.
3. 전국 비교는 `시도 추정합계`와 `전국 공식 분기 GDP/GRDP 경계`의 WAPE로 해석한다.
4. 실질 연쇄가격 계열은 엄밀한 회계 항등식처럼 완전 가산되는 값이 아닐 수 있으므로, 전국 합계 비교는 외부 집계검증 지표이지 공식 국민계정 대체값이 아니다.
5. 일부 광역시는 시군구 원천표의 경계연도·행정구역 변경(예: 군위군, 특별자치도 전환)을 별도 경계재정렬로 보강해야 한다.

## 산출물

- `nationwide/outputs/sigungu_industry_quarterly_predictions.csv`
- `nationwide/outputs/sido_quarterly_grdp_validation.csv`
- `nationwide/outputs/operating_point_sido_grdp_validation.csv`
- `nationwide/outputs/national_gdp_coverage_validation.csv`
- `nationwide/outputs/national_gdp_yearly_summary.csv`
- `nationwide/data_sources_and_release_cycles.md`
