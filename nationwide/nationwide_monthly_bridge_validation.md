# 전국 시군구 월별 GVA bridge 및 집계검증

생성시각: 2026-07-29T14:38:29+09:00

## 1. 목적

기존 `시군구×업종×분기` 추정값을 월 단위 운영자료로 확장했다. 월별 산출은 분기 추정값을 바꾸지 않고, 보유 월별 활동지표가 있는 업종은 해당 월별 지표 비중으로, 없는 업종은 분기 내 균등분할로 배분한다.

## 2. 산출 요약

| monthly_rows | tracks | years_min | years_max | sigungu_count | activity_count | indicator_rows_pct | fallback_equal_split_rows_pct | max_abs_quarter_reaggregation_error_eok | bad_quarter_cells_gt_1won_equiv | bad_month_count_cells | bad_month_share_sum_cells | negative_month_value_cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 357,240 | 2 | 2021 | 2025 | 229 | 13 | 6.452805 | 93.547195 | 0.000000 | 0 | 0 | 0 | 0 |

## 3. 사용한 월별 시간경로

| 업종군 | 월별 배분 기준 | 비고 |
| --- | --- | --- |
| 광업, 제조업 | 시도별 제조업 생산지수 | 광업+제조업 통합 GVA의 월중 변화 후보. 세부 광업 분리는 별도 actual 부족으로 보류 |
| 서비스 세부업종 | 분기 내 균등분할 | 현재 로컬 서비스업생산지수는 분기자료로 확인되어 월별 bridge에는 사용하지 않음 |
| 건설업·기타산업 및 순생산물세 등 | 분기 내 균등분할 | 조달청 PPS/건설 활동자료가 coverage gate를 통과하기 전까지 보수적 bridge |

## 4. 활동지표 coverage

| track | activity_group | monthly_indicator_coverage | monthly_indicator_source | rows | estimated_sum_eok | city_count | year_min | year_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| prior_year_province_anchor | 건설업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 5,296,779.484 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 건설업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 5,296,537.751 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 공공 행정, 국방·사회보장 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 7,045,428.518 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 공공 행정, 국방·사회보장 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 7,045,494.924 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 광업, 제조업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,214 | 4,992,505.815 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 광업, 제조업 | fallback_equal_split | equal_split_no_monthly_indicator | 2,214 | 5,002,930.924 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 광업, 제조업 | monthly_indicator | 시도별 제조업 생산지수 | 11,526 | 24,742,640.388 | 204 | 2021 | 2025 |
| recursive_no_target_actual | 광업, 제조업 | monthly_indicator | 시도별 제조업 생산지수 | 11,526 | 24,761,626.091 | 204 | 2021 | 2025 |
| prior_year_province_anchor | 교육 서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 4,982,533.810 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 교육 서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 4,982,491.794 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 금융 및 보험업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 6,168,239.802 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 금융 및 보험업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 6,168,178.206 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 도매 및 소매업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,941,569.646 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 도매 및 소매업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,941,569.598 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 문화 및 기타서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 3,243,655.626 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 문화 및 기타서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 3,243,961.297 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 보건 및 사회복지업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 6,193,572.076 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 보건 및 사회복지업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 6,193,478.824 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 부동산업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,164,610.885 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 부동산업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,164,622.353 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 사업서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,426,053.974 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 사업서비스업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 8,425,991.380 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 숙박 및 음식점업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 2,427,475.298 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 숙박 및 음식점업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 2,427,508.458 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 운수 및 창고업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 4,550,687.522 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 운수 및 창고업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 4,572,195.074 | 207 | 2021 | 2025 |
| prior_year_province_anchor | 정보통신업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 5,246,004.075 | 207 | 2021 | 2025 |
| recursive_no_target_actual | 정보통신업 | fallback_equal_split | equal_split_no_monthly_indicator | 13,740 | 5,248,766.608 | 207 | 2021 | 2025 |

## 5. 균등분할 fallback이 큰 업종

| activity_group | fallback_sum_eok | fallback_rows |
| --- | --- | --- |
| 도매 및 소매업 | 17,883,139.244 | 27,480 |
| 사업서비스업 | 16,852,045.354 | 27,480 |
| 부동산업 | 16,329,233.239 | 27,480 |
| 공공 행정, 국방·사회보장 | 14,090,923.443 | 27,480 |
| 보건 및 사회복지업 | 12,387,050.900 | 27,480 |
| 금융 및 보험업 | 12,336,418.008 | 27,480 |
| 건설업 | 10,593,317.235 | 27,480 |
| 정보통신업 | 10,494,770.683 | 27,480 |
| 광업, 제조업 | 9,995,436.739 | 4,428 |
| 교육 서비스업 | 9,965,025.605 | 27,480 |
| 운수 및 창고업 | 9,122,882.596 | 27,480 |
| 문화 및 기타서비스업 | 6,487,616.923 | 27,480 |
| 숙박 및 음식점업 | 4,854,983.756 | 27,480 |

## 6. 분기 재집계 및 월 share 무결성 검증

월별 추정값은 원 분기 추정값을 보존해야 한다. 따라서 각 `track×시도×시군구×업종×분기`별 월합과 원 분기값을 비교했다.

| max_abs_quarter_reaggregation_error_eok | bad_quarter_cells_gt_1won_equiv | bad_month_count_cells | bad_month_share_sum_cells | negative_month_value_cells |
| --- | --- | --- | --- | --- |
| 0.0000000000 | 0 | 0 | 0 | 0 |

## 7. 해석

1. 이 산출물은 월별 official actual 검증이 아니라 **상위 분기 추정값을 보존하는 월별 운영 bridge**다.
2. 월별 활동지표가 있는 광업·제조업은 월중 변화를 반영한다.
3. 서비스업 rolling 지수는 현재 로컬 파일 기준 분기자료이므로 월별 자료처럼 쓰지 않는다.
4. 건설업은 PPS 계약정보가 2015~2025 coverage gate를 통과하지 못했으므로 월별 시간경로를 자동채택하지 않았다.
5. `bad_quarter_cells_gt_1won_equiv=0`이면 월별 추정값을 다시 분기로 합산했을 때 기존 분기 추정과 실질적으로 완전히 일치한다.

## 8. 산출물

- `nationwide/outputs/sigungu_industry_monthly_predictions.csv`
- `nationwide/outputs/monthly_bridge_quarter_reaggregation_audit.csv`
- `nationwide/outputs/monthly_bridge_share_integrity_audit.csv`
- `nationwide/outputs/monthly_bridge_indicator_coverage.csv`
- `nationwide/outputs/monthly_bridge_summary.csv`
