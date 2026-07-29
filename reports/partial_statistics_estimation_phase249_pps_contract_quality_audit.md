# Phase249 조달청 공사계약 수집 품질 감사

생성시각: 2026-07-29T18:09:01+09:00

## 1. 요약

| months_seen | months_quality_complete | adoptable_years | invalid_manifest_period_rows | rows_collected | manifest_rows_collected | api_total_count_seen | raw_partial_preserved_months | overall_collection_rate_pct | mean_province_match_rate_pct | mean_sigungu_match_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 132 | 21 | 1 | 0 | 613,790 | 706,697 | 910,191 | 8 | 67.44 | 87.62 | 73.85 |

## 2. 첫 미완료 원인

| period | api_total_count | manifest_rows_collected | rows_collected | pages_collected | raw_json_count | raw_partial_preserved | monthly_csv_exists | collection_rate_pct | manifest_complete | manifest_ok | manifest_error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 201610 | 31,271 | 25,974 | 0 | 26 | 26 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201611 | 42,330 | 16,983 | 0 | 17 | 17 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201612 | 49,126 | 13,986 | 0 | 14 | 14 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201701 | 18,287 | 10,989 | 0 | 11 | 11 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201702 | 30,273 | 8,991 | 0 | 9 | 9 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201703 | 48,184 | 8,991 | 0 | 9 | 9 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201704 | 38,846 | 5,994 | 0 | 6 | 6 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201705 | 38,084 | 999 | 0 | 1 | 1 | True | False | 0.00 | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201706 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201707 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201708 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | <HTTPError 429: 'Too Many Requests'> |
| 201709 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | <HTTPError 429: 'Too Many Requests'> |

첫 미완료 월은 후속 수집 재개의 시작점이다. `HTTPError 429: Too Many Requests`가 남아 있으면 해당 시점의 API 일일/분당 제한 또는 서버 측 제한에 걸린 것으로 보고, 부분 수집 파일은 downstream 건설업 route 검증에 투입하지 않는다.

## 3. 월별 수집·매칭 품질

| period | api_total_count | manifest_rows_collected | rows_collected | pages_collected | raw_json_count | raw_partial_preserved | monthly_csv_exists | collection_rate_pct | manifest_complete | quality_complete | duplicate_contract_id_count | missing_or_zero_amount_count | province_match_rate_pct | sigungu_match_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 201501 | 12,590 | 12,590 | 12,590 | 13 | 13 | False | True | 100.00 | True | True | 0 | 5 | 89.60 | 69.48 |
| 201502 | 19,852 | 19,852 | 19,852 | 20 | 20 | False | True | 100.00 | True | True | 0 | 3 | 89.56 | 69.42 |
| 201503 | 34,956 | 34,956 | 34,956 | 35 | 35 | False | True | 100.00 | True | True | 0 | 4 | 86.98 | 78.73 |
| 201504 | 33,096 | 33,096 | 33,096 | 34 | 34 | False | True | 100.00 | True | True | 0 | 5 | 88.18 | 78.95 |
| 201505 | 27,735 | 27,735 | 27,735 | 28 | 28 | False | True | 100.00 | True | True | 0 | 3 | 88.44 | 78.89 |
| 201506 | 36,064 | 36,064 | 36,064 | 37 | 37 | False | True | 100.00 | True | True | 0 | 3 | 86.39 | 76.17 |
| 201507 | 27,994 | 27,994 | 27,994 | 29 | 29 | False | True | 100.00 | True | True | 0 | 7 | 89.41 | 70.26 |
| 201508 | 21,760 | 21,760 | 21,760 | 22 | 22 | False | True | 100.00 | True | True | 0 | 5 | 87.32 | 71.57 |
| 201509 | 25,721 | 25,721 | 25,721 | 26 | 26 | False | True | 100.00 | True | True | 0 | 2 | 87.61 | 71.71 |
| 201510 | 28,273 | 28,273 | 28,273 | 29 | 29 | False | True | 100.00 | True | True | 0 | 6 | 86.66 | 75.02 |
| 201511 | 34,745 | 34,745 | 34,745 | 35 | 35 | False | True | 100.00 | True | True | 0 | 1 | 85.13 | 74.03 |
| 201512 | 42,221 | 42,221 | 42,221 | 43 | 43 | False | True | 100.00 | True | True | 0 | 4 | 80.81 | 68.87 |
| 201601 | 13,276 | 13,276 | 13,276 | 14 | 14 | False | True | 100.00 | True | True | 0 | 3 | 88.51 | 69.78 |
| 201602 | 22,300 | 22,300 | 22,300 | 23 | 23 | False | True | 100.00 | True | True | 0 | 1 | 89.24 | 69.93 |
| 201603 | 41,811 | 41,811 | 41,811 | 42 | 42 | False | True | 100.00 | True | True | 0 | 3 | 88.67 | 81.00 |
| 201604 | 34,416 | 34,416 | 34,416 | 35 | 35 | False | True | 100.00 | True | True | 0 | 2 | 87.40 | 79.23 |
| 201605 | 33,789 | 33,789 | 33,789 | 34 | 34 | False | True | 100.00 | True | True | 0 | 5 | 88.33 | 79.25 |
| 201606 | 39,351 | 39,351 | 39,351 | 40 | 40 | False | True | 100.00 | True | True | 0 | 2 | 86.96 | 76.77 |
| 201607 | 29,848 | 29,848 | 29,848 | 30 | 30 | False | True | 100.00 | True | True | 0 | 2 | 89.53 | 69.16 |
| 201608 | 27,509 | 27,509 | 27,509 | 28 | 28 | False | True | 100.00 | True | True | 0 | 1 | 87.47 | 71.26 |
| 201609 | 26,483 | 26,483 | 26,483 | 27 | 27 | False | True | 100.00 | True | True | 0 | 0 | 87.83 | 71.39 |
| 201610 | 31,271 | 25,974 | 0 | 26 | 26 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201611 | 42,330 | 16,983 | 0 | 17 | 17 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201612 | 49,126 | 13,986 | 0 | 14 | 14 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201701 | 18,287 | 10,989 | 0 | 11 | 11 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201702 | 30,273 | 8,991 | 0 | 9 | 9 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201703 | 48,184 | 8,991 | 0 | 9 | 9 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201704 | 38,846 | 5,994 | 0 | 6 | 6 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201705 | 38,084 | 999 | 0 | 1 | 1 | True | False | 0.00 | False | False | 0 | 0 | 0.00 | 0.00 |
| 201706 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201707 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201708 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201709 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201710 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201711 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201712 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201801 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201802 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201803 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201804 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201805 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201806 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201807 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201808 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201809 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201810 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201811 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201812 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201901 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201902 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201903 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201904 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201905 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201906 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201907 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201908 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201909 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201910 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201911 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |
| 201912 | 0 | 0 | 0 | 0 | 0 | False | False |  | False | False | 0 | 0 | 0.00 | 0.00 |

## 4. 연도별 채택 가능성 게이트

| year | months_seen | months_quality_complete | min_collection_rate_pct | mean_province_match_rate_pct | mean_sigungu_match_rate_pct | adoptable_year |
| --- | --- | --- | --- | --- | --- | --- |
| 2015 | 12 | 12 | 100.00 | 87.17 | 73.59 | True |
| 2016 | 12 | 9 | 0.00 | 66.16 | 55.65 | False |
| 2017 | 12 | 0 | 0.00 | 0.00 | 0.00 | False |
| 2018 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2019 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2020 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2021 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2022 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2023 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2024 | 12 | 0 |  | 0.00 | 0.00 | False |
| 2025 | 12 | 0 |  | 0.00 | 0.00 | False |

## 5. 판정 기준

| 항목 | 기준 | 해석 |
| --- | --- | --- |
| 월별 수집률 | 99.9% 이상 | 미완료 월은 본 검증에서 제외하거나 재수집 |
| 연도 채택 | 12개월 모두 `quality_complete=True` | 연간 GVA 검증에 포함 가능한 최소 조건 |
| 시도 매칭률 | 95% 이상 권장 | 광역시도 분석 채택 조건 |
| 시군구 매칭률 | 80~90% 이상 권장 | 시군구 분석 채택 조건 |
| 중복 계약번호 | dedup 전후 비교 | 계약변경/중복 가능성 확인 |
| 금액 0/결측 | 별도 집계 | 금액 share 산식에서 제외/보조 처리 |

## 6. 기준연도 100 지수 혼재 처리 원칙

2015=100, 2020=100 등 기준이 다른 지수형 입력은 사용 전 공통 bridge year로 재기준화한다. 기본식은 `rebased = raw / raw[bridge_year] * 100`이며, 2020년 충격 가능성이 큰 지표는 2019년·2021년 bridge 민감도도 같이 본다. 재기준화 후에는 전국합/시도합 보존과 연도별 변동률 왜곡 여부를 감사한다.

## 7. 주의

조달청 계약정보의 지역 텍스트는 계약기관·수요기관·공사명에 섞여 있다. 따라서 이 감사의 `matched_city`는 실제 공사 수행지를 확정한 값이 아니라, 공개 계약정보 텍스트 기반 보수적 지역 귀속값이다.
