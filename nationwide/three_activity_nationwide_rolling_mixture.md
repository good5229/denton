# 전국 3개 업종 rolling mixture 라우팅 실험

생성시각: 2026-07-29T00:47:21+09:00

## 목적

과학자 검토 의견에 따라 모든 업종을 특화하지 않고 `건설업`, `운수 및 창고업`, `숙박 및 음식점업` 3개 업종만 대상으로 활동지표 route를 시험했다.

## 누수 방지 규칙

| 항목 | 적용 |
| --- | --- |
| 목표연도 actual | route 선택에는 사용하지 않음. 선택 후 평가에만 사용 |
| 후보 가중치 | 0%, 25%, 50%, 75%, 100% |
| 선택 기준 | target year 이전 연도의 누적 절대오차 개선 |
| 최근 악화 방지 | 최근 2년 prior 중 후보가 기준선보다 악화된 행이 있으면 미채택 |
| 대상 업종 수 | 3개로 고정 |

## 운영시점별 결과

| 사용분기수 | 검증셀 | 채택셀 | official_sum_eok | baseline_abs_error_sum_eok | selected_abs_error_sum_eok | 기준10pct초과 | 선택10pct초과 | 기준20pct초과 | 선택20pct초과 | 기준WAPE_pct | 선택WAPE_pct | 변화_pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 227 | 70 | 11,495,703.870 | 1,085,222.249 | 994,155.679 | 85 | 82 | 21 | 17 | 9.440 | 8.648 | -0.792 |
| 2 | 227 | 79 | 11,495,703.870 | 925,572.129 | 799,239.216 | 60 | 50 | 12 | 6 | 8.051 | 6.953 | -1.099 |
| 3 | 227 | 70 | 11,495,703.870 | 894,098.490 | 738,510.302 | 56 | 44 | 9 | 4 | 7.778 | 6.424 | -1.353 |
| 4 | 227 | 80 | 11,495,703.870 | 868,271.955 | 712,274.481 | 52 | 38 | 10 | 6 | 7.553 | 6.196 | -1.357 |

## 업종별 결과

| 업종 | 사용분기수 | 검증셀 | 채택셀 | official_sum_eok | baseline_abs_error_sum_eok | selected_abs_error_sum_eok | 기준10pct초과 | 선택10pct초과 | 기준20pct초과 | 선택20pct초과 | 기준최대오차율_pct | 선택최대오차율_pct | 기준WAPE_pct | 선택WAPE_pct | 변화_pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 건설업 | 1 | 77 | 26 | 5,069,329.460 | 418,603.390 | 363,313.817 | 24 | 23 | 6 | 5 | 37.219 | 34.921 | 8.258 | 7.167 | -1.091 |
| 건설업 | 2 | 77 | 26 | 5,069,329.460 | 411,137.659 | 367,618.984 | 26 | 20 | 6 | 3 | 38.894 | 51.036 | 8.110 | 7.252 | -0.858 |
| 건설업 | 3 | 77 | 24 | 5,069,329.460 | 406,859.489 | 363,837.972 | 26 | 22 | 4 | 1 | 41.202 | 26.792 | 8.026 | 7.177 | -0.849 |
| 건설업 | 4 | 77 | 24 | 5,069,329.460 | 403,074.519 | 392,120.941 | 28 | 25 | 5 | 4 | 42.106 | 47.903 | 7.951 | 7.735 | -0.216 |
| 숙박 및 음식점업 | 1 | 70 | 22 | 2,089,621.020 | 205,667.849 | 220,465.170 | 29 | 32 | 8 | 9 | 24.311 | 32.824 | 9.842 | 10.550 | 0.708 |
| 숙박 및 음식점업 | 2 | 70 | 27 | 2,089,621.020 | 123,186.291 | 137,053.327 | 13 | 17 | 0 | 0 | 17.569 | 17.569 | 5.895 | 6.559 | 0.664 |
| 숙박 및 음식점업 | 3 | 70 | 16 | 2,089,621.020 | 100,208.075 | 90,517.294 | 7 | 7 | 0 | 0 | 13.640 | 14.200 | 4.796 | 4.332 | -0.464 |
| 숙박 및 음식점업 | 4 | 70 | 26 | 2,089,621.020 | 81,546.693 | 62,754.141 | 2 | 1 | 0 | 0 | 11.724 | 11.724 | 3.902 | 3.003 | -0.899 |
| 운수 및 창고업 | 1 | 80 | 22 | 4,336,753.390 | 460,951.010 | 410,376.693 | 32 | 27 | 7 | 3 | 46.935 | 27.919 | 10.629 | 9.463 | -1.166 |
| 운수 및 창고업 | 2 | 80 | 26 | 4,336,753.390 | 391,248.180 | 294,566.906 | 21 | 13 | 6 | 3 | 39.443 | 39.443 | 9.022 | 6.792 | -2.229 |
| 운수 및 창고업 | 3 | 80 | 30 | 4,336,753.390 | 387,030.926 | 284,155.036 | 23 | 15 | 5 | 3 | 37.739 | 37.739 | 8.924 | 6.552 | -2.372 |
| 운수 및 창고업 | 4 | 80 | 30 | 4,336,753.390 | 383,650.743 | 257,399.399 | 22 | 12 | 5 | 2 | 36.098 | 26.190 | 8.846 | 5.935 | -2.911 |

## 채택 route 요약

| 업종 | 사용분기수 | 채택route | 가중치 | 채택셀수 |
| --- | --- | --- | --- | --- |
| 건설업 | 1 | regional_construction_orders_bok_12_24q | 0.250 | 11 |
| 건설업 | 1 | regional_construction_orders_raw | 0.250 | 5 |
| 건설업 | 1 | regional_construction_orders_bok_12_24q | 0.500 | 4 |
| 건설업 | 1 | regional_construction_orders_bok_12_24q | 0.750 | 3 |
| 건설업 | 1 | regional_construction_orders_bok_12_24q | 1.000 | 3 |
| 건설업 | 2 | regional_construction_orders_bok_12_24q | 0.250 | 11 |
| 건설업 | 2 | regional_construction_orders_bok_12_24q | 0.500 | 6 |
| 건설업 | 2 | regional_construction_orders_bok_12_24q | 0.750 | 4 |
| 건설업 | 2 | regional_construction_orders_raw | 0.250 | 3 |
| 건설업 | 2 | regional_construction_orders_bok_12_24q | 1.000 | 2 |
| 건설업 | 3 | regional_construction_orders_bok_12_24q | 0.250 | 9 |
| 건설업 | 3 | regional_construction_orders_bok_12_24q | 0.500 | 5 |
| 건설업 | 3 | regional_construction_orders_bok_12_24q | 0.750 | 4 |
| 건설업 | 3 | regional_construction_orders_raw | 0.250 | 3 |
| 건설업 | 3 | regional_construction_orders_bok_12_24q | 1.000 | 2 |
| 건설업 | 3 | regional_construction_orders_raw | 0.500 | 1 |
| 건설업 | 4 | regional_construction_orders_bok_12_24q | 0.250 | 7 |
| 건설업 | 4 | regional_construction_orders_bok_12_24q | 0.750 | 4 |
| 건설업 | 4 | regional_construction_orders_bok_12_24q | 1.000 | 4 |
| 건설업 | 4 | regional_construction_orders_raw | 0.250 | 4 |
| 건설업 | 4 | regional_construction_orders_bok_12_24q | 0.500 | 3 |
| 건설업 | 4 | regional_construction_orders_raw | 1.000 | 2 |
| 숙박 및 음식점업 | 1 | regional_service_production_index_I | 1.000 | 15 |
| 숙박 및 음식점업 | 1 | regional_service_production_index_I | 0.750 | 4 |
| 숙박 및 음식점업 | 1 | regional_service_production_index_I | 0.250 | 2 |
| 숙박 및 음식점업 | 1 | regional_service_production_index_I | 0.500 | 1 |
| 숙박 및 음식점업 | 2 | regional_service_production_index_I | 1.000 | 20 |
| 숙박 및 음식점업 | 2 | regional_service_production_index_I | 0.500 | 4 |
| 숙박 및 음식점업 | 2 | regional_service_production_index_I | 0.250 | 2 |
| 숙박 및 음식점업 | 2 | regional_service_production_index_I | 0.750 | 1 |
| 숙박 및 음식점업 | 3 | regional_service_production_index_I | 1.000 | 10 |
| 숙박 및 음식점업 | 3 | regional_service_production_index_I | 0.500 | 4 |
| 숙박 및 음식점업 | 3 | regional_service_production_index_I | 0.750 | 2 |
| 숙박 및 음식점업 | 4 | regional_service_production_index_I | 1.000 | 11 |
| 숙박 및 음식점업 | 4 | regional_service_production_index_I | 0.750 | 8 |
| 숙박 및 음식점업 | 4 | regional_service_production_index_I | 0.250 | 5 |
| 숙박 및 음식점업 | 4 | regional_service_production_index_I | 0.500 | 2 |
| 운수 및 창고업 | 1 | regional_service_production_index_H | 1.000 | 14 |
| 운수 및 창고업 | 1 | regional_service_production_index_H | 0.250 | 4 |
| 운수 및 창고업 | 1 | regional_service_production_index_H | 0.500 | 2 |
| 운수 및 창고업 | 1 | regional_service_production_index_H | 0.750 | 2 |
| 운수 및 창고업 | 2 | regional_service_production_index_H | 0.750 | 8 |
| 운수 및 창고업 | 2 | regional_service_production_index_H | 0.250 | 7 |
| 운수 및 창고업 | 2 | regional_service_production_index_H | 1.000 | 6 |
| 운수 및 창고업 | 2 | regional_service_production_index_H | 0.500 | 5 |
| 운수 및 창고업 | 3 | regional_service_production_index_H | 1.000 | 12 |
| 운수 및 창고업 | 3 | regional_service_production_index_H | 0.250 | 8 |
| 운수 및 창고업 | 3 | regional_service_production_index_H | 0.500 | 5 |
| 운수 및 창고업 | 3 | regional_service_production_index_H | 0.750 | 5 |
| 운수 및 창고업 | 4 | regional_service_production_index_H | 1.000 | 10 |
| 운수 및 창고업 | 4 | regional_service_production_index_H | 0.750 | 8 |
| 운수 및 창고업 | 4 | regional_service_production_index_H | 0.250 | 7 |
| 운수 및 창고업 | 4 | regional_service_production_index_H | 0.500 | 5 |

## 운영시점별 권고

아래 권고는 평균 WAPE만 보지 않고, 10% 초과 셀·20% 초과 셀·최대오차율이 모두 악화되지 않는 경우만 채택으로 본다.

| 업종 | 사용분기수 | 기준WAPE_pct | 선택WAPE_pct | 기준10pct초과 | 선택10pct초과 | 기준20pct초과 | 선택20pct초과 | 기준최대오차율_pct | 선택최대오차율_pct | 권고 | 사유 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 건설업 | 1 | 8.258 | 7.167 | 24 | 23 | 6 | 5 | 37.219 | 34.921 | rolling mixture 채택 | 모든 guardrail 통과 |
| 건설업 | 2 | 8.110 | 7.252 | 26 | 20 | 6 | 3 | 38.894 | 51.036 | baseline 유지 | 평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과 |
| 건설업 | 3 | 8.026 | 7.177 | 26 | 22 | 4 | 1 | 41.202 | 26.792 | rolling mixture 채택 | 모든 guardrail 통과 |
| 건설업 | 4 | 7.951 | 7.735 | 28 | 25 | 5 | 4 | 42.106 | 47.903 | baseline 유지 | 평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과 |
| 숙박 및 음식점업 | 1 | 9.842 | 10.550 | 29 | 32 | 8 | 9 | 24.311 | 32.824 | baseline 유지 | 평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과 |
| 숙박 및 음식점업 | 2 | 5.895 | 6.559 | 13 | 17 | 0 | 0 | 17.569 | 17.569 | baseline 유지 | 평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과 |
| 숙박 및 음식점업 | 3 | 4.796 | 4.332 | 7 | 7 | 0 | 0 | 13.640 | 14.200 | baseline 유지 | 평균WAPE/10%초과/20%초과/최대오차율 중 하나 이상 악화 또는 WAPE 10% 초과 |
| 숙박 및 음식점업 | 4 | 3.902 | 3.003 | 2 | 1 | 0 | 0 | 11.724 | 11.724 | rolling mixture 채택 | 모든 guardrail 통과 |
| 운수 및 창고업 | 1 | 10.629 | 9.463 | 32 | 27 | 7 | 3 | 46.935 | 27.919 | rolling mixture 채택 | 모든 guardrail 통과 |
| 운수 및 창고업 | 2 | 9.022 | 6.792 | 21 | 13 | 6 | 3 | 39.443 | 39.443 | rolling mixture 채택 | 모든 guardrail 통과 |
| 운수 및 창고업 | 3 | 8.924 | 6.552 | 23 | 15 | 5 | 3 | 37.739 | 37.739 | rolling mixture 채택 | 모든 guardrail 통과 |
| 운수 및 창고업 | 4 | 8.846 | 5.935 | 22 | 12 | 5 | 2 | 36.098 | 26.190 | rolling mixture 채택 | 모든 guardrail 통과 |

## 판단

- 이 실험은 target-year actual을 route 선택에 쓰지 않았으므로 no-worse 사후선택보다 보수적이다.
- 최근 prior 악화가 있으면 미채택하는 규칙 때문에 채택셀 수가 적다. 이는 성능 과장을 막는 대신 개선폭을 제한한다.
- 결과가 기준선보다 악화되는 운영시점이나 업종은 자동 채택 대상에서 제외해야 한다.
- 따라서 `숙박 및 음식점업` Q1~Q2, 최대오차율이 악화되는 일부 `건설업` 운영시점은 평균 WAPE만 좋아도 공개 성능으로 채택하지 않는다.
