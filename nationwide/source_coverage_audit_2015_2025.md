# 2015~2025 전국 자료 coverage 감사

생성시각: 2026-07-29T18:09:13+09:00

## 1. 목적

전국 광역시도·시군구 월/분기 GVA·GRDP 추정에 사용하는 주요 자료군이 2015~2025 기간, 지역 범위, 기준연도, 공표/수집 상태 측면에서 충분한지 점검했다. 이 감사는 자료가 존재한다는 사실과 운영 채택 가능성을 구분한다.

## 2. 상태 요약

| coverage_status | source_count |
| --- | --- |
| blocked_api_incomplete | 1 |
| covers_2015_2025 | 6 |
| limited_period | 1 |
| metadata_ok | 1 |
| partial_by_definition | 4 |
| partial_complete_months | 1 |
| usable_for_2021_2025_backtest_with_limits | 5 |

## 3. 자료별 판정

| source_id | label | exists | rows | period_min | period_max | year_min | year_max | province_count | sigungu_count | index_base | expected_scope | coverage_status | pps_months_complete | pps_complete_periods | pps_first_incomplete_period | pps_manifest_rows_collected | pps_manifest_total_count | pps_partial_raw_months | pps_rate_limited_months | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_annual_gva | 시군구 경제활동별 연간 실질 GVA | True | 12844 | 2019 | 2023 | 2019 | 2023 | 17 | 207 | real_value_not_index | nationwide_with_publication_gaps | usable_for_2021_2025_backtest_with_limits |  |  |  |  |  |  |  | 공표 시도별 연도 범위가 다르며 일부 광역시는 2023 시군구 원천이 없다. |
| sido_quarterly_grdp_experimental | 시도별 분기 실질 GRDP/GDP 실험적 통계 | True | 16560 | 2015Q1 | 2026Q1 | 2015 | 2026 |  |  | real_value_not_index | nationwide | covers_2015_2025 |  |  |  |  |  |  |  | 세종 단층처리와 순생산물세 bridge에 사용. |
| national_quarterly_gdp | 전국 분기 GDP | True | 2508 | 201501 | 202504 | 2015 | 2025 |  |  | real_value_not_index | national | covers_2015_2025 |  |  |  |  |  |  |  | 전국 경계 WAPE는 외부 일관성 참고지표로만 해석. |
| manufacturing_production_index | 시도별 제조업 광공업생산지수 | True | 792 | 201501 | 202504 | 2015 | 2025 | 18 |  | 2020=100 | nationwide | covers_2015_2025 |  |  |  |  |  |  |  | 공개 actual 검증은 광업+제조업 합산 경계에서 수행. |
| mining_production_index | 시도별 광업 생산지수 | True | 576 | 201501 | 202504 | 2015 | 2025 | 14 |  | 2020=100 | nationwide | covers_2015_2025 |  |  |  |  |  |  |  | 일부 기간/지역 결측 가능. |
| manufacturing_detail_production_index | 제조업 세부 생산지수 | True | 2145 | 202001 | 202505 | 2020 | 2025 |  |  | 2020=100 | partial_industry | partial_by_definition |  |  |  |  |  |  |  | 전체 KSIC 중분류를 덮지 못하므로 보조 후보. |
| service_production_index | 시도별 서비스업생산지수 | True | 10472 | 201501 | 202504 | 2015 | 2025 | 17 |  | 2020=100 | nationwide | covers_2015_2025 |  |  |  |  |  |  |  | 상반기 조기점검 보조에는 유효하나 자동채택은 rolling gate 필요. |
| service_detail_national_index | 전국 세부 서비스업생산지수 | True | 6412 | 201901 | 202404 | 2019 | 2024 |  |  | 2020=100 | national_detail | usable_for_2021_2025_backtest_with_limits |  |  |  |  |  |  |  | 지역 차원이 없어 시군구 공간배분 단독 근거로 사용 금지. |
| service_industry_national_monthly_index | 전국 산업별 서비스업생산지수 | True | 17420 | 202001 | 202505 | 2020 | 2025 |  |  | 2020=100 | national_industry | usable_for_2021_2025_backtest_with_limits |  |  |  |  |  |  |  | 전국 산업별 월 지수이므로 공간배분 근거로 사용 금지. 지역별 분기 총량은 그대로 보존한다. |
| all_industry_national_monthly_index | 전국 전산업생산지수 원지수 | True | 325 | 202001 | 202505 | 2020 | 2025 |  |  | 2020=100 | national_broad_industry | usable_for_2021_2025_backtest_with_limits |  |  |  |  |  |  |  | 전국 월 지수이므로 공간배분 근거로 사용 금지. 조달청 PPS 미통과 상태에서도 분기 내 시간경로로만 사용한다. |
| electricity_sigungu_monthly | 시군구 전력사용량 historical as-of 패널 | True | 69673 | 202001 | 202307 | 2020 | 2023 |  |  | usage_not_index | nationwide_or_large_panel | usable_for_2021_2025_backtest_with_limits |  |  |  |  |  |  |  | 업종귀속이 거칠어 단독 route보다 보조 후보. |
| electricity_sigungu_current_monthly | 시군구 전력사용량 최신 월별 원천 | True | 148616 | 202501 | 202604 | 2025 | 2026 | 17 | 207 | usage_not_index | nationwide_current_snapshot | limited_period |  |  |  |  |  |  |  | 최신 공표분 중심 자료. 과거 backtest에는 historical as-of 패널을 우선 사용. |
| electricity_gas_production_index | 전기·가스 생산지수 | True | 792 | 201501 | 202504 | 2015 | 2025 | 18 |  | 2020=100 | nationwide | covers_2015_2025 |  |  |  |  |  |  |  | 지수형 입력. 기준연도 bridge 감사 대상. |
| pps_contract_info | 조달청 나라장터 공사계약 정보 | True | 132 | 201501 | 202512 | 2015 | 2025 |  |  | amount_not_index | nationwide_public_contracts | blocked_api_incomplete | 21 |  | 201610 | 706697 | 910191 | 8 | 109 | API 429로 전량 미완료. 공공공사 계약액이지 전체 건설업 actual이 아니다. |
| pps_bid_notice_robust | 조달청 나라장터 공사공고 robust cache | True | 63736 | 202104 | 202108 | 2021 | 2021 |  |  | amount_not_index | nationwide_public_bid_notices | partial_complete_months | 4 | 202104,202105,202106,202107 | 202108 |  |  |  |  | numRows=100 raw cache 기준 완전월만 성능감사에 투입. 공사공고는 전체 건설업 actual이 아니다. |
| cals_contracts | CALS 공사계약/목록 | True | 1683 | 1997년 | 전체 | 1997 | 2027 |  |  | amount_not_index | public_soc_partial | partial_by_definition |  |  |  |  |  |  |  | 민간건축 및 전체 건설업 대표자료 아님. |
| lh_notices | LH 분양임대공고 | True | 9465 | 202101 | 202312 | 2021 | 2023 |  |  | count_not_index | public_housing_land_partial | partial_by_definition |  |  |  |  |  |  |  | 금액자료가 아니므로 단독 GVA 배분 기준으로 사용 금지. |
| seoul_redevelopment | 서울 도시정비사업 통계 | True | 476 |  |  |  |  |  |  | not_index | local_only | partial_by_definition |  |  |  |  |  |  |  | 전국 원본이 아니므로 전국 일반화에는 별도 지방정부 자료 필요. |
| index_base_bridge | 지수 기준연도 bridge 감사 | True | 5 | 201501 | 201901 | 2015 | 2019 |  |  | bridge_metadata | all_index_inputs | metadata_ok |  |  |  |  |  |  |  | 현재 로컬 주요 지수는 2020=100 소급계열. |

## 4. 핵심 판정

- `시도별 분기 GRDP/GDP`, 생산·서비스 지수 계열은 2015~2025 전국/시도 검증에 대체로 사용 가능하다.
- 시군구 연간 GVA actual은 공식 공표 범위가 2020~2023 중심이고 시도별 누락연도가 있다. 따라서 2015~2025 전기간 시군구 actual 검증은 불가능하며, 2021~2025 backtest는 직전연도/재귀 기준값과 상위 집계검증을 병행해야 한다.
- 조달청 공사계약은 전국 원본 성격이 맞지만 API 429로 전량 수집이 끝나지 않았다. 부분 raw가 남은 월도 품질완료 월로 승격하지 않고, 현재는 건설업 전국 route 채택이 아니라 수집·품질게이트 보류 상태다.
- 조달청 공사공고 robust cache는 공사계약 API 제한 중 수집 가능한 보조자료이나, 완전월만 성능감사에 투입한다. 현재 완전월과 부분월은 자료별 판정 표의 `pps_complete_periods`, `pps_first_incomplete_period`로 분리한다.
- CALS, LH, 서울 도시정비사업은 보조자료이며, 각각 공공/SOC·공공주택·서울 정비사업으로 범위가 제한된다.
- 현재 로컬 주요 지수는 2020=100 소급계열이므로 2015=100/2020=100 혼재 왜곡은 확인되지 않았다. 향후 legacy 2015=100 계열이 추가되면 bridge year 재기준화가 필요하다.

## 5. 산출물

- `nationwide/outputs/source_coverage_audit_2015_2025.csv`
