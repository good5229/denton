# 전국 5개년 범용성 검증

생성시각: 2026-07-29T00:12:47+09:00

## 목적

2021~2025년 5개년 전체를 사용해 현재 방식이 특정 1~2개 연도에만 우연히 맞은 것인지, 아니면 전국 17개 시도에 대해 비교적 안정적으로 작동하는지 점검했다.

검증의 핵심은 하위 추정값을 그대로 믿는 것이 아니라, 분기누적 운영시점별 추정치를 시도 연간 actual 및 전국 GDP/GRDP 경계값으로 다시 집계해 오차를 확인하는 것이다.

## 검증 범위

| 항목 | 값 |
| --- | --- |
| 검증연도 | 2021~2025년 |
| 지역 | 17개 시도 |
| 운영시점 | 1분기, 1~2분기, 1~3분기, 공표 후 정밀화 |
| 트랙 | 엄격 속보형, 직전연도 시도총량 보정형 |
| 검증행 | 680행 |

## 5개년 안정성 요약

| 트랙 | 사용분기수 | 모의운영시점 | 5개년평균_연간환산WAPE_pct | 연도별최대_연간환산WAPE_pct | 연도별표준편차_pct | 시도연도최대오차율_pct | 10pct초과_시도연도수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 1 | 1분기+1개월 | 1.644 | 2.194 | 0.437 | 6.654 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 1.135 | 1.612 | 0.274 | 5.361 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 1.050 | 1.414 | 0.211 | 4.749 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 1.071 | 1.239 | 0.112 | 4.076 | 0.000 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 1.889 | 2.516 | 0.630 | 9.384 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 1.390 | 2.333 | 0.595 | 8.073 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 1.293 | 2.079 | 0.521 | 7.453 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 1.311 | 1.902 | 0.434 | 6.763 | 0.000 |

## 전국 경계 안정성

| 트랙 | 연도수 | 5개년평균_전국경계WAPE_pct | 연도별최대_전국경계WAPE_pct | 연도별표준편차_pct |
| --- | --- | --- | --- | --- |
| prior_year_province_anchor | 5 | 0.059 | 0.127 | 0.046 |
| recursive_no_target_actual | 5 | 0.042 | 0.069 | 0.027 |

## 상대적으로 어려운 지역

| 트랙 | 사용분기수 | 모의운영시점 | 시도 | 5개년_연간환산WAPE_pct | 최대연도오차율_pct | 5pct초과연도수 | 10pct초과연도수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 1 | 1분기+1개월 | 인천 | 3.582 | 5.198 | 1.000 | 0.000 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 울산 | 3.544 | 6.122 | 2.000 | 0.000 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 세종 | 3.533 | 5.686 | 1.000 | 0.000 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 대구 | 3.427 | 5.858 | 2.000 | 0.000 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 세종 | 3.127 | 5.259 | 1.000 | 0.000 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 충북 | 3.049 | 9.384 | 1.000 | 0.000 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 충북 | 2.840 | 6.654 | 1.000 | 0.000 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 울산 | 2.659 | 6.122 | 1.000 | 0.000 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 강원 | 2.564 | 5.082 | 1.000 | 0.000 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 대구 | 2.549 | 4.918 | 0.000 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 울산 | 3.081 | 5.198 | 2.000 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 인천 | 3.070 | 4.591 | 0.000 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 대구 | 2.676 | 5.525 | 1.000 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 충북 | 2.597 | 8.073 | 1.000 | 0.000 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 전북 | 2.596 | 3.647 | 0.000 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 충북 | 2.260 | 5.361 | 1.000 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 경북 | 2.125 | 3.368 | 0.000 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 세종 | 2.086 | 3.723 | 0.000 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 인천 | 1.909 | 4.591 | 0.000 | 0.000 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 대구 | 1.801 | 3.846 | 0.000 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 울산 | 2.958 | 4.680 | 0.000 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 인천 | 2.807 | 4.185 | 0.000 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 대구 | 2.690 | 6.030 | 1.000 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 충북 | 2.673 | 7.453 | 1.000 | 0.000 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 전북 | 2.505 | 3.501 | 0.000 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 충북 | 2.106 | 4.749 | 0.000 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 인천 | 1.960 | 4.185 | 0.000 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 경북 | 1.884 | 2.961 | 0.000 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 대구 | 1.815 | 3.416 | 0.000 | 0.000 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 전남 | 1.724 | 3.934 | 0.000 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 울산 | 3.168 | 4.486 | 0.000 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 충북 | 2.931 | 6.763 | 1.000 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 인천 | 2.910 | 4.354 | 0.000 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 대구 | 2.480 | 6.086 | 1.000 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 충북 | 2.391 | 4.076 | 0.000 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 인천 | 2.089 | 4.004 | 0.000 | 0.000 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 전북 | 2.083 | 3.345 | 0.000 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 울산 | 1.817 | 3.798 | 0.000 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 제주 | 1.708 | 2.807 | 0.000 | 0.000 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 전남 | 1.602 | 3.223 | 0.000 | 0.000 |

## 업종별 5개년 안정성 진단

아래 표는 시도 총량이 아니라 `시도×업종×연도` 검증행을 업종별로 다시 묶은 것이다. 따라서 전국·시도 총량 검증보다 더 엄격하다.

| 트랙 | 사용분기수 | 모의운영시점 | 업종 | 5개년_업종WAPE_pct | 시도연도최대오차율_pct | 10pct초과_시도연도수 | 20pct초과_시도연도수 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recursive_no_target_actual | 1 | 1분기+1개월 | 운수 및 창고업 | 10.525 | 46.935 | 33 | 7 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 숙박 및 음식점업 | 9.581 | 24.929 | 35 | 11 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 숙박 및 음식점업 | 8.750 | 24.929 | 34 | 11 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 건설업 | 8.324 | 37.219 | 28 | 6 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 운수 및 창고업 | 7.383 | 25.852 | 22 | 2 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 건설업 | 6.141 | 31.714 | 17 | 3 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 문화 및 기타서비스업 | 4.707 | 15.311 | 5 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 문화 및 기타서비스업 | 4.340 | 15.311 | 3 | 0 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 광업, 제조업 | 4.330 | 21.261 | 10 | 1 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 정보통신업 | 3.713 | 29.232 | 20 | 4 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 광업, 제조업 | 3.443 | 14.828 | 3 | 0 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 도매 및 소매업 | 2.948 | 11.890 | 5 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 도매 및 소매업 | 2.892 | 11.890 | 2 | 0 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 정보통신업 | 2.846 | 27.124 | 7 | 1 |
| recursive_no_target_actual | 1 | 1분기+1개월 | 사업서비스업 | 2.754 | 20.440 | 6 | 1 |
| prior_year_province_anchor | 1 | 1분기+1개월 | 금융 및 보험업 | 2.477 | 6.608 | 0 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 운수 및 창고업 | 8.933 | 39.443 | 21 | 6 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 건설업 | 8.165 | 38.894 | 30 | 6 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 건설업 | 5.768 | 28.495 | 16 | 2 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 숙박 및 음식점업 | 5.700 | 18.242 | 17 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 운수 및 창고업 | 5.448 | 25.600 | 12 | 3 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 숙박 및 음식점업 | 4.739 | 18.242 | 16 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 광업, 제조업 | 4.019 | 19.663 | 10 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 문화 및 기타서비스업 | 3.311 | 15.173 | 4 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 정보통신업 | 3.046 | 30.512 | 19 | 4 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 광업, 제조업 | 3.011 | 13.314 | 2 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 문화 및 기타서비스업 | 2.913 | 11.550 | 2 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 금융 및 보험업 | 2.355 | 6.091 | 0 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 금융 및 보험업 | 2.338 | 13.616 | 1 | 0 |
| recursive_no_target_actual | 2 | 1~2분기+1개월 | 사업서비스업 | 2.295 | 17.859 | 6 | 0 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 정보통신업 | 2.180 | 23.749 | 7 | 1 |
| prior_year_province_anchor | 2 | 1~2분기+1개월 | 도매 및 소매업 | 1.971 | 7.452 | 0 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 운수 및 창고업 | 8.831 | 37.739 | 23 | 5 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 건설업 | 8.069 | 41.202 | 30 | 4 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 건설업 | 5.559 | 25.176 | 17 | 2 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 운수 및 창고업 | 5.273 | 26.439 | 13 | 3 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 숙박 및 음식점업 | 4.593 | 14.346 | 10 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 광업, 제조업 | 3.803 | 18.723 | 10 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 숙박 및 음식점업 | 3.456 | 14.346 | 9 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 문화 및 기타서비스업 | 2.977 | 14.416 | 4 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 광업, 제조업 | 2.766 | 12.424 | 1 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 정보통신업 | 2.720 | 30.556 | 17 | 4 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 문화 및 기타서비스업 | 2.500 | 11.389 | 2 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 금융 및 보험업 | 2.131 | 5.609 | 0 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 사업서비스업 | 2.058 | 18.018 | 4 | 0 |
| recursive_no_target_actual | 3 | 1~3분기+1개월 | 금융 및 보험업 | 1.959 | 13.101 | 1 | 0 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 정보통신업 | 1.858 | 23.942 | 8 | 1 |
| prior_year_province_anchor | 3 | 1~3분기+1개월 | 사업서비스업 | 1.606 | 18.018 | 3 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 운수 및 창고업 | 8.762 | 36.098 | 22 | 5 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 건설업 | 7.983 | 42.106 | 33 | 5 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 건설업 | 5.476 | 23.363 | 19 | 3 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 운수 및 창고업 | 5.143 | 26.190 | 12 | 3 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 광업, 제조업 | 3.754 | 17.928 | 8 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 숙박 및 음식점업 | 3.690 | 11.724 | 2 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 문화 및 기타서비스업 | 2.858 | 14.812 | 4 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 광업, 제조업 | 2.700 | 11.672 | 1 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 정보통신업 | 2.612 | 30.556 | 17 | 4 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 숙박 및 음식점업 | 2.533 | 11.724 | 1 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 문화 및 기타서비스업 | 2.336 | 11.482 | 2 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 금융 및 보험업 | 2.070 | 6.036 | 0 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 사업서비스업 | 2.045 | 17.997 | 5 | 0 |
| recursive_no_target_actual | 4 | 공표 후 정밀화 | 보건 및 사회복지업 | 1.808 | 15.866 | 1 | 0 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 정보통신업 | 1.750 | 24.330 | 9 | 1 |
| prior_year_province_anchor | 4 | 공표 후 정밀화 | 부동산업 | 1.566 | 9.481 | 0 | 0 |

## 판단

1. 5개년 평균 기준으로 전국 17개 시도 연간환산 WAPE는 대부분 1~2%대에 머문다.
2. 엄격 속보형도 시도 총량 기준으로는 10% 초과 시도-연도 조합이 발생하지 않아, “전국 범용 적용 후보”로 볼 수 있다.
3. 1분기+1개월만 사용해도 5개년 평균 WAPE가 2% 안팎이고, 1~2분기 및 1~3분기 누적 자료를 쓰면 더 안정된다.
4. 다만 전국 경계 WAPE는 전국 계절비중을 사용하는 구조 때문에 작게 나올 수 있으므로, 범용성 판단의 핵심 근거는 시도별 5개년 WAPE와 최대오차율이다.
5. 업종별로 보면 운수 및 창고업, 건설업, 숙박 및 음식점업, 정보통신업은 일부 시도-연도에서 10~20% 초과 오차가 남는다. 이 단계는 전국 총량 모니터링에는 충분하지만, 업종별 정책배분에는 직접 활동자료를 추가한 보강모형이 필요하다.
6. 상대적으로 어려운 지역은 인천·울산·세종·대구·충북 등이다. 제조업·항만·대기업 사업장·단층도시 구조처럼 지역 고유 충격이 큰 곳에서는 직접 활동자료를 추가하면 더 좋아질 가능성이 높다.
7. 결론적으로 이 방식은 1~2개 연도의 우연한 적합이 아니라, 2021~2025년 5개년과 17개 시도 전역에서 작동하는 범용 운영형 추정체계 후보로 판단된다. 단, 공식통계 대체가 아니라 상위 actual 집계검증을 동반한 개발통계/모니터링 체계로 표현해야 한다.
