# 시도 분기 GRDP 장기 검증: 2016~2025

생성시각: 2026-07-29T14:42:27+09:00

## 목적

시군구 annual actual의 공표범위 한계와 별도로, 통계청 실험적 시도 분기 GRDP 표가 제공하는 2015~2025 장기 actual을 이용해 `직전연도 연간값 × 전국 분기 움직임` 규칙이 10년 창에서도 안정적인지 검증했다.

2015년은 전년도 기준값이 없는 초기화 연도이므로 자료 coverage에는 포함하되 성능 검증은 2016~2025년으로 수행했다.

## 검증 설계

| 항목 | 내용 |
| --- | --- |
| 자료 | `phase211_sido_quarterly_xlsx_long.csv` |
| 검증연도 | 2016~2025년 |
| 지역 | 17개 시도 |
| 업종 | 광업·제조업, 건설업, 서비스 세부업종, 기타산업 및 순생산물세 |
| 예측입력 | 전년도 시도×업종 연간값, 목표연도 전국×업종 분기 움직임 |
| 금지 | 목표 시도×업종 분기 actual을 예측 입력으로 사용하지 않음 |
| 해석 | 시군구 검증의 대체가 아니라 2015~2025 장기 안정성 보조검증 |

## 운영시점별 GRDP 성능

| 트랙 | 사용분기수 | 모의운영시점 | 연도수 | 시도수 | 연간환산WAPE_pct | 최대시도연도오차율_pct | 10pct초과_시도연도수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 1 | 1분기+1개월 | 10 | 17 | 1.778 | 11.755 | 1 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 10 | 17 | 1.402 | 8.613 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 10 | 17 | 1.321 | 8.948 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 10 | 17 | 1.320 | 9.391 | 0 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 10 | 17 | 6.526 | 30.562 | 47 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 10 | 17 | 6.350 | 27.484 | 48 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 10 | 17 | 6.330 | 27.243 | 50 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 10 | 17 | 6.340 | 27.838 | 48 |

## 연도별 취약 구간

| 트랙 | 사용분기수 | 모의운영시점 | 연도 | 시도수 | 연간환산WAPE_pct | 최대시도오차율_pct | 10pct초과_시도수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 1 | 1분기+1개월 | 2024 | 17 | 8.493 | 21.799 | 8 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 2025 | 17 | 8.490 | 17.356 | 8 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 2022 | 17 | 8.282 | 25.337 | 9 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 2023 | 17 | 8.231 | 16.311 | 8 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 2021 | 17 | 7.985 | 23.787 | 6 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 2020 | 17 | 2.828 | 11.755 | 1 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 2017 | 17 | 2.213 | 5.020 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 2021 | 17 | 2.194 | 3.154 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 2018 | 17 | 1.815 | 3.931 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 2025 | 17 | 1.787 | 4.101 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 2025 | 17 | 8.431 | 18.066 | 8 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 2024 | 17 | 8.278 | 20.423 | 8 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 2022 | 17 | 8.257 | 25.101 | 8 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 2023 | 17 | 8.079 | 17.665 | 8 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 2021 | 17 | 7.597 | 27.484 | 6 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 2020 | 17 | 2.427 | 8.613 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 2017 | 17 | 2.095 | 4.323 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 2018 | 17 | 1.662 | 4.227 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 2025 | 17 | 1.612 | 3.818 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 2016 | 17 | 1.470 | 5.774 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 2025 | 17 | 8.524 | 18.968 | 10 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 2022 | 17 | 8.240 | 25.416 | 8 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 2024 | 17 | 8.201 | 19.908 | 7 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 2023 | 17 | 8.002 | 18.426 | 9 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 2021 | 17 | 7.660 | 26.947 | 6 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 2020 | 17 | 2.403 | 8.948 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 2017 | 17 | 2.007 | 4.540 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 2018 | 17 | 1.578 | 4.081 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 2025 | 17 | 1.414 | 3.282 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 2016 | 17 | 1.385 | 5.598 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 2025 | 17 | 8.610 | 19.016 | 10 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 2022 | 17 | 8.252 | 24.306 | 7 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 2024 | 17 | 8.169 | 19.257 | 7 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 2023 | 17 | 7.980 | 19.661 | 9 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 2021 | 17 | 7.792 | 26.103 | 6 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 2020 | 17 | 2.407 | 9.391 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 2017 | 17 | 2.108 | 4.182 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 2018 | 17 | 1.469 | 4.356 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 2016 | 17 | 1.340 | 5.648 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 2025 | 17 | 1.239 | 3.335 | 0 |

## 업종별 취약 구간

| 트랙 | 사용분기수 | 모의운영시점 | 업종 | 시도연도수 | 업종WAPE_pct | 최대시도연도오차율_pct | 10pct초과_시도연도수 | 20pct초과_시도연도수 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 1 | 1분기+1개월 | 광업, 제조업 | 170 | 15.785 | 49.750 | 91 | 50 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 건설업 | 170 | 15.289 | 98.718 | 111 | 57 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 운수 및 창고업 | 170 | 10.173 | 58.387 | 81 | 34 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 공공 행정, 국방·사회보장 | 170 | 8.239 | 38.438 | 49 | 19 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 숙박 및 음식점업 | 170 | 7.469 | 45.113 | 58 | 18 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 건설업 | 170 | 6.783 | 31.714 | 48 | 8 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 금융 및 보험업 | 170 | 6.687 | 42.572 | 53 | 18 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 운수 및 창고업 | 170 | 6.351 | 35.860 | 35 | 4 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 숙박 및 음식점업 | 170 | 5.882 | 25.382 | 41 | 12 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 사업서비스업 | 170 | 5.724 | 41.515 | 51 | 24 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 광업, 제조업 | 170 | 3.684 | 21.428 | 7 | 1 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 문화 및 기타서비스업 | 170 | 3.655 | 15.311 | 6 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 사업서비스업 | 170 | 2.889 | 22.505 | 14 | 2 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 정보통신업 | 170 | 2.476 | 27.097 | 7 | 1 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 광업, 제조업 | 170 | 15.784 | 43.571 | 92 | 47 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 건설업 | 170 | 15.004 | 93.861 | 105 | 60 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 운수 및 창고업 | 170 | 9.785 | 53.129 | 80 | 29 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 공공 행정, 국방·사회보장 | 170 | 8.216 | 38.598 | 49 | 19 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 금융 및 보험업 | 170 | 6.567 | 42.972 | 55 | 16 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 건설업 | 170 | 6.221 | 28.495 | 44 | 7 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 숙박 및 음식점업 | 170 | 5.662 | 31.685 | 50 | 12 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 기타산업 및 순생산물세 | 170 | 5.570 | 24.897 | 47 | 6 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 운수 및 창고업 | 170 | 5.179 | 28.221 | 23 | 5 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 숙박 및 음식점업 | 170 | 3.849 | 24.982 | 22 | 1 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 광업, 제조업 | 170 | 3.472 | 16.418 | 4 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 문화 및 기타서비스업 | 170 | 2.556 | 13.276 | 5 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 사업서비스업 | 170 | 2.288 | 18.538 | 13 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 금융 및 보험업 | 170 | 2.191 | 16.786 | 2 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 광업, 제조업 | 170 | 15.785 | 44.393 | 95 | 45 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 건설업 | 170 | 14.892 | 90.549 | 103 | 61 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 운수 및 창고업 | 170 | 9.752 | 54.151 | 78 | 29 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 공공 행정, 국방·사회보장 | 170 | 8.217 | 38.322 | 49 | 19 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 금융 및 보험업 | 170 | 6.525 | 43.792 | 53 | 13 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 건설업 | 170 | 6.025 | 25.728 | 45 | 7 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 기타산업 및 순생산물세 | 170 | 5.562 | 24.683 | 49 | 5 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 숙박 및 음식점업 | 170 | 5.343 | 29.422 | 47 | 9 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 운수 및 창고업 | 170 | 5.054 | 27.829 | 24 | 6 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 광업, 제조업 | 170 | 3.334 | 17.084 | 3 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 숙박 및 음식점업 | 170 | 3.223 | 24.331 | 14 | 1 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 문화 및 기타서비스업 | 170 | 2.269 | 13.888 | 5 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 금융 및 보험업 | 170 | 2.089 | 16.576 | 2 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 사업서비스업 | 170 | 2.004 | 18.018 | 9 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 광업, 제조업 | 170 | 15.763 | 45.755 | 94 | 47 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 건설업 | 170 | 14.810 | 91.769 | 101 | 57 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 운수 및 창고업 | 170 | 9.745 | 53.849 | 75 | 27 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 공공 행정, 국방·사회보장 | 170 | 8.220 | 38.373 | 49 | 19 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 금융 및 보험업 | 170 | 6.569 | 43.995 | 53 | 15 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 건설업 | 170 | 5.862 | 26.974 | 43 | 6 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 기타산업 및 순생산물세 | 170 | 5.589 | 24.438 | 50 | 5 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 사업서비스업 | 170 | 5.333 | 37.645 | 50 | 24 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 운수 및 창고업 | 170 | 4.980 | 27.259 | 25 | 6 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 광업, 제조업 | 170 | 3.282 | 18.189 | 4 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 숙박 및 음식점업 | 170 | 2.632 | 25.120 | 6 | 1 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 문화 및 기타서비스업 | 170 | 2.178 | 13.597 | 5 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 금융 및 보험업 | 170 | 2.031 | 17.064 | 2 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 기타산업 및 순생산물세 | 170 | 1.991 | 23.183 | 4 | 1 |

## 분기 직접검증 경계

| 트랙 | 연도수 | 연평균_분기WAPE_pct | 연도최대_분기WAPE_pct | 최대분기오차율_pct |
| --- | --- | --- | --- | --- |
| prior_year_province_anchor | 10 | 1.685 | 2.511 | 11.359 |
| recursive_no_target_actual | 10 | 6.343 | 8.695 | 30.416 |

## 판정

1. 2016~2025 장기 창에서도 시도 총량 GRDP는 대체로 낮은 WAPE를 유지하는지 확인한다.
2. 업종별로 10% 초과 시도연도 조합이 남는 경우, 해당 업종은 시군구 세부 추정에서도 직접 활동자료 route를 우선 검토해야 한다.
3. 이 검증은 목표 시도 분기 actual을 입력하지 않는 장기 안정성 감사다. 다만 전국 분기 움직임 자체는 사후 백테스트 빈티지이므로, 실시간 운용 성과라고 주장하려면 원천별 공표시점 빈티지를 별도로 잠가야 한다.

## 산출물

- `nationwide/outputs/sido_long_window_activity_quarterly_predictions.csv`
- `nationwide/outputs/sido_long_window_activity_quarterly_validation.csv`
- `nationwide/outputs/sido_long_window_grdp_quarterly_validation.csv`
- `nationwide/outputs/sido_long_window_operating_grdp_validation.csv`
- `nationwide/outputs/sido_long_window_operating_activity_validation.csv`
- `nationwide/outputs/sido_long_window_operating_summary.csv`
- `nationwide/outputs/sido_long_window_yearly_summary.csv`
- `nationwide/outputs/sido_long_window_activity_summary.csv`
- `nationwide/outputs/sido_long_window_quarter_boundary_summary.csv`
