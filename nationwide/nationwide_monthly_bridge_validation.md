# 전국 시군구 월별 GVA bridge 및 집계검증

생성시각: 2026-07-29T15:05:07+09:00

## 1. 목적

기존 `시군구×업종×분기` 추정값을 월 단위 운영자료로 확장했다. 월별 산출은 분기 추정값을 바꾸지 않고, 보유 월별 활동지표가 있는 업종은 해당 월별 지표 비중으로, 없는 업종은 분기 내 균등분할로 배분한다.

## 2. 산출 요약

| monthly_rows | tracks | years_min | years_max | sigungu_count | activity_count | indicator_rows_pct | fallback_equal_split_rows_pct | max_abs_quarter_reaggregation_error_eok | bad_quarter_cells_gt_1won_equiv | bad_month_count_cells | bad_month_share_sum_cells | negative_month_value_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 357,240 | 2 | 2021 | 2025 | 229 | 13 | 84.914343 | 15.085657 | 0.000000 | 0 | 0 | 0 | 0 |

`indicator_rows_pct`는 **월별 시간경로를 적용한 행 비중**이다. 월별 official actual 검증 비중이나 시군구 공간배분 설명력 비중이 아니며, 지역별·업종별 분기 추정 총량은 변경하지 않는다.

## 3. 사용한 월별 시간경로

| 업종군 | 월별 배분 기준 | 비고 |
| --- | --- | --- |
| 광업, 제조업 | 시도별 제조업 생산지수 | 광업+제조업 통합 GVA의 월중 변화 후보. 세부 광업 분리는 별도 actual 부족으로 보류 |
| 서비스 세부업종 | 전국 산업별 서비스업생산지수 | 지역별 배분에는 사용하지 않고, 같은 업종·분기의 시군구 GVA를 3개월로 나누는 시간경로로만 사용 |
| 건설업 | 전국 전산업생산지수 원지수의 건설업 항목 | 조달청 PPS가 coverage gate를 통과하기 전까지 지역별 공간배분은 기존 분기값 보존 |
| 공공 행정, 국방·사회보장 | 전국 전산업생산지수 원지수의 공공행정 항목 | 지역별 배분에는 사용하지 않고 분기 내 시간경로로만 사용 |
| 기타산업 및 순생산물세 등 | 분기 내 균등분할 | 월별 직접 지표가 없는 항목은 보수적 bridge |

## 4. 활동지표 coverage

| track | activity_group | monthly_indicator_coverage | monthly_indicator_source | rows | estimated_sum_eok | city_count | year_min | year_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 건설업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 766,146.799 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 건설업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 766,080.166 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 건설업 | monthly_indicator | 전국 전산업생산지수 원지수 | 11,679 | 4,530,632.685 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 건설업 | monthly_indicator | 전국 전산업생산지수 원지수 | 11,679 | 4,530,457.585 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,078,109.428 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,078,139.729 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | monthly_indicator | 전국 전산업생산지수 원지수 | 11,679 | 5,967,319.091 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | monthly_indicator | 전국 전산업생산지수 원지수 | 11,679 | 5,967,355.195 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 광업, 제조업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,214 | 4,992,505.815 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 광업, 제조업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,214 | 5,002,930.924 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 광업, 제조업 | monthly_indicator | 시도별 제조업 생산지수 | 11,526 | 24,742,640.388 | 204 | 2021 | 2025 |
| recursive_no_target_actual | 광업, 제조업 | monthly_indicator | 시도별 제조업 생산지수 | 11,526 | 24,761,626.091 | 204 | 2021 | 2025 |
| prior_year_province_anchor | 교육 서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 738,751.215 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 교육 서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 738,731.942 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 교육 서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 4,243,782.595 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 교육 서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 4,243,759.853 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 금융 및 보험업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 987,773.955 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 금융 및 보험업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 987,738.190 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 금융 및 보험업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 5,180,465.847 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 금융 및 보험업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 5,180,440.016 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 도매 및 소매업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,332,733.688 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 도매 및 소매업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,332,733.662 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 도매 및 소매업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 7,608,835.959 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 도매 및 소매업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 7,608,835.936 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 문화 및 기타서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 497,915.140 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 문화 및 기타서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 498,031.345 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 문화 및 기타서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 2,745,740.486 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 문화 및 기타서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 2,745,929.952 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 보건 및 사회복지업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,023,552.615 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 보건 및 사회복지업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,023,500.975 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 보건 및 사회복지업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 5,170,019.461 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 보건 및 사회복지업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 5,169,977.849 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 부동산업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,244,248.542 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 부동산업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,244,348.496 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 부동산업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 6,920,362.344 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 부동산업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 6,920,273.858 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 사업서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,339,403.592 | 207 | 2025 | 2025 |
| recursive_no_target_actual | 사업서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,061 | 1,339,371.848 | 207 | 2025 | 2025 |
| prior_year_province_anchor | 사업서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 7,086,650.382 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 사업서비스업 | monthly_indicator | 전국 산업별 서비스업생산지수 | 11,679 | 7,086,619.532 | 207 | 2021 | 2025 |

## 5. 활동지표 완전분기 범위

월별 지표는 해당 분기의 3개월 값이 모두 있을 때만 사용했다. 2025년 최신월이 일부만 있는 경우에는 부분월을 외삽하지 않고 균등분할로 돌렸다.

| activity_group | monthly_indicator_source | complete_quarters | first_complete_quarter | last_complete_quarter |
| --- | --- | --- | --- | --- |
| 광업, 제조업 | 시도별 제조업 생산지수 | 17 | 2021Q1 | 2025Q1 |
| 교육 서비스업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 금융 및 보험업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 도매 및 소매업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 문화 및 기타서비스업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 보건 및 사회복지업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 부동산업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 사업서비스업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 숙박 및 음식점업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 운수 및 창고업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 정보통신업 | 전국 산업별 서비스업생산지수 | 17 | 2021Q1 | 2025Q1 |
| 건설업 | 전국 전산업생산지수 원지수 | 17 | 2021Q1 | 2025Q1 |
| 공공 행정, 국방·사회보장 | 전국 전산업생산지수 원지수 | 17 | 2021Q1 | 2025Q1 |

## 6. 균등분할 fallback이 큰 업종

| activity_group | fallback_sum_eok | fallback_rows |
| --- | --- | --- |
| 광업, 제조업 | 9,995,436.739 | 4,428 |
| 사업서비스업 | 2,678,775.440 | 4,122 |
| 도매 및 소매업 | 2,665,467.350 | 4,122 |
| 부동산업 | 2,488,597.037 | 4,122 |
| 공공 행정, 국방·사회보장 | 2,156,249.157 | 4,122 |
| 보건 및 사회복지업 | 2,047,053.591 | 4,122 |
| 금융 및 보험업 | 1,975,512.145 | 4,122 |
| 운수 및 창고업 | 1,647,745.379 | 4,122 |
| 정보통신업 | 1,647,023.056 | 4,122 |
| 건설업 | 1,532,226.964 | 4,122 |
| 교육 서비스업 | 1,477,483.157 | 4,122 |
| 문화 및 기타서비스업 | 995,946.485 | 4,122 |
| 숙박 및 음식점업 | 764,442.183 | 4,122 |

## 7. 분기 재집계 및 월 share 무결성 검증

월별 추정값은 원 분기 추정값을 보존해야 한다. 따라서 각 `track×시도×시군구×업종×분기`별 월합과 원 분기값을 비교했다.

이 검증은 월별 정확도 검증이 아니라 **상위 분기값 보존성 검증**이다. `bad_quarter_cells_gt_1won_equiv=0`은 월별로 쪼갠 값을 다시 합치면 기존 분기 추정값과 일치한다는 뜻이다.

| max_abs_quarter_reaggregation_error_eok | bad_quarter_cells_gt_1won_equiv | bad_month_count_cells | bad_month_share_sum_cells | negative_month_value_cells |
| --- | --- | --- | --- | --- |
| 0.0000000000 | 0 | 0 | 0 | 0 |

## 8. 해석

1. 이 산출물은 월별 official actual 검증이 아니라 **상위 분기 추정값을 보존하는 월별 운영 bridge**다.
2. 광업·제조업은 시도별 월별 생산지수로 월중 변화를 반영한다.
3. 서비스업·건설업·공공행정은 전국 월별 지수만 사용하므로 **공간배분 근거가 아니라 시간배분 근거**다.
4. 조달청 PPS 계약정보가 2015~2025 coverage gate를 통과하기 전까지 건설업의 시군구 공간배분 route는 자동채택하지 않는다.
5. `bad_quarter_cells_gt_1won_equiv=0`이면 월별 추정값을 다시 분기로 합산했을 때 기존 분기 추정과 실질적으로 완전히 일치한다.

## 9. 산출물

- `nationwide/outputs/sigungu_industry_monthly_predictions.csv`
- `nationwide/outputs/monthly_bridge_quarter_reaggregation_audit.csv`
- `nationwide/outputs/monthly_bridge_share_integrity_audit.csv`
- `nationwide/outputs/monthly_bridge_indicator_coverage.csv`
- `nationwide/outputs/monthly_bridge_indicator_period_coverage.csv`
- `nationwide/outputs/monthly_bridge_summary.csv`
