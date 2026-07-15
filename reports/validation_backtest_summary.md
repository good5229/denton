# 레벨별 정확도 검증 요약

생성일: 2026-07-15

## 핵심 해석

현재 직접적인 예측 정확도는 `official_actual`과 비교 가능한 시도 연간 대분류에서 가장 강하게 검증된다. 시군구 연간 대분류의 낮은 오차는 예측 성능이 아니라 공식 연간 벤치마크와의 회계 정합성이다. 시군구 중분류·소분류와 읍면동은 아직 공식 actual이 없으므로 proxy 및 상위합 정합성 검증으로 관리해야 한다.

## Official Actual 비교

| level | industry_depth | value_role | rows | comparable_rows | mape | aggregate_percent_error | wmape_like |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sido | large | forecast | 2574 | 2002 | 6.407741 | 0.379331 | 0.379331 |

## Benchmark 정합성

| level | industry_depth | value_role | rows | comparable_rows | mape | aggregate_percent_error | wmape_like |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu | large | benchmarked_allocation | 16396 | 16396 | 0.0 | 0.0 | 0.0 |

## Proxy 또는 미검증 구간

| level | industry_depth | actual_role | value_role | rows | comparable_rows |
| --- | --- | --- | --- | --- | --- |
| emd | large | proxy | proxy_allocation | 148322 | 0 |
| sigungu | class | proxy | proxy_allocation | 200876 | 0 |
| sigungu | class | proxy_unavailable | proxy_allocation | 15 | 0 |
| sigungu | middle | proxy | proxy_allocation | 58219 | 0 |
| sigungu | middle | proxy_unavailable | proxy_allocation | 10263 | 0 |
| sigungu | small | proxy | proxy_allocation | 139653 | 0 |
| sigungu | small | proxy_unavailable | proxy_allocation | 3136 | 0 |

## Forecast Actual 미공표 구간

| level | industry_depth | actual_role | value_role | rows | comparable_rows |
| --- | --- | --- | --- | --- | --- |
| sigungu | large | future_or_unavailable | forecast | 11103 | 0 |

## Official Actual 기준 상위 오차

| area_name | sector_name | year | predicted_value | actual_value | absolute_percent_error |
| --- | --- | --- | --- | --- | --- |
| 광주광역시 | 전기 가스 증기 및 공기 조절 공급업 | 2023 | 650166.860691 | 175398.0 | 270.680886150925 |
| 대전광역시 | 광업 | 2021 | 4336.550211 | 1679.0 | 158.281727873734 |
| 서울특별시 | 광업 | 2023 | 14510.585013 | 6276.0 | 131.207536854685 |
| 울산광역시 | 광업 | 2023 | 50998.633392 | 22705.0 | 124.614108751376 |
| 울산광역시 | 광업 | 2017 | 200513.852218 | 93383.0 | 114.722007451035 |
| 대전광역시 | 광업 | 2017 | 2754.579682 | 1286.0 | 114.197486936236 |
| 부산광역시 | 전기 가스 증기 및 공기 조절 공급업 | 2017 | 1910371.939929 | 965302.0 | 97.904069392687 |
| 대구광역시 | 광업 | 2021 | 2279.798669 | 1207.0 | 88.881414167357 |
| 세종특별자치시 | 농업 임업 및 어업 | 2018 | 291066.781119 | 161025.0 | 80.758752441546 |
| 제주특별자치도 | 광업 | 2019 | 17284.63489 | 9676.0 | 78.634093530384 |
| 충청남도 | 광업 | 2019 | 173901.665807 | 97571.0 | 78.230894227793 |
| 울산광역시 | 전기 가스 증기 및 공기 조절 공급업 | 2018 | 1911219.468015 | 1102363.0 | 73.374783806695 |

## 다음 검증 과제

1. 시군구 대분류는 연간 actual을 숨기는 rolling backtest를 별도 구성해야 한다.
2. 중분류·소분류는 공식 actual 부재로 인해 제조업 proxy actual, 서비스업 세부지수, 상위합 정합성을 분리 평가해야 한다.
3. 읍면동은 서울 등 일부 지역의 외부 준actual을 확보해 proxy share의 안정성을 검증해야 한다.
4. ML 모델은 official actual 검증 구간을 주평가 대상으로 두고, benchmark/proxy 행은 낮은 가중치 또는 보조 진단으로 사용해야 한다.
