# Phase186 C00 제조업 지표 후보 Screen

## 목적

Phase185는 C00 제조업 잔여오차가 중분류별로 다르며, C00 전체 보정은 위험하다고 판정했다. Phase186은 로컬에 이미 있는 제조업 관련 지표를 중분류별로 screen한다.

중요한 제한은 다음과 같다.

- 이 단계는 **운영 채택이 아니라 후보 screen**이다.
- 고양·포항 target actual은 사후 평가에만 사용한다.
- 2023 시군구×중분류 부가가치 지표처럼 예측 대상과 매우 가까운 자료는 성능이 좋아도 **누수위험 후보**로 기각한다.
- 속보 후보는 공표시점 및 외부검증이 끝나기 전까지 채택하지 않는다.

## 후보 요약

| 지역 | 후보ID | 지표 | 트랙 | 셀 | 커버 | 기준 WAPE(%) | 후보 WAPE(%) | 오차감소(억원) | 악화셀 | 20%초과 전 | 20%초과 후 | 판정 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | pbiz_fin_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 21 | 20 | 28.425 | 31.677 | -648.793 | 12 | 12 | 13 | reject |
| 고양시 | phase120_personal_business_sales_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 21 | 20 | 28.425 | 31.937 | -700.759 | 11 | 12 | 14 | reject |
| 고양시 | pbiz_fin_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 21 | 19 | 28.425 | 32.415 | -796.142 | 10 | 12 | 11 | reject |
| 고양시 | phase120_personal_business_sales_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 21 | 21 | 28.425 | 32.827 | -878.306 | 12 | 12 | 15 | reject |
| 고양시 | phase120_personal_business_profile_count_all | 개인사업자 기본정보 사업자 행수 | 검토 후보 | 21 | 21 | 28.425 | 34.522 | -1216.439 | 14 | 12 | 17 | reject |
| 고양시 | pbiz_fin_asset_pos_lag2021 | 개인사업자 양수 자산합계 | 속보 후보 | 21 | 19 | 28.425 | 37.477 | -1805.907 | 12 | 12 | 12 | reject |
| 고양시 | pbiz_fin_profit_pos_lag2021 | 개인사업자 양수 영업이익합계 | 속보 후보 | 21 | 19 | 28.425 | 37.552 | -1820.804 | 12 | 12 | 12 | reject |
| 고양시 | pbiz_fin_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 21 | 19 | 28.425 | 37.855 | -1881.28 | 12 | 12 | 12 | reject |
| 고양시 | pbiz_fin_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 21 | 19 | 28.425 | 37.855 | -1881.28 | 12 | 12 | 12 | reject |
| 고양시 | pbiz_fin_profit_pos_all_vintage_unverified | 개인사업자 양수 영업이익합계 | 정밀화 후보 | 21 | 20 | 28.425 | 40.812 | -2471.19 | 14 | 12 | 12 | reject |
| 고양시 | phase120_personal_business_sales_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 21 | 20 | 28.425 | 41.359 | -2580.337 | 14 | 12 | 13 | reject |
| 고양시 | phase120_personal_business_sales_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 21 | 20 | 28.425 | 41.359 | -2580.337 | 14 | 12 | 13 | reject |
| 고양시 | pbiz_fin_abs_sale_all_vintage_unverified | 개인사업자 절대 매출합계 | 정밀화 후보 | 21 | 20 | 28.425 | 41.382 | -2584.85 | 15 | 12 | 12 | reject |
| 고양시 | pbiz_fin_positive_sale_all_vintage_unverified | 개인사업자 양수 매출합계 | 정밀화 후보 | 21 | 20 | 28.425 | 41.382 | -2584.85 | 15 | 12 | 12 | reject |
| 고양시 | pbiz_fin_asset_pos_all_vintage_unverified | 개인사업자 양수 자산합계 | 정밀화 후보 | 21 | 20 | 28.425 | 41.62 | -2632.454 | 15 | 12 | 12 | reject |
| 고양시 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 개인사업자 절대 매출합계 | 정밀화 후보 | 21 | 21 | 28.425 | 45.059 | -3318.374 | 15 | 12 | 16 | reject |
| 고양시 | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 개인사업자 양수 매출합계 | 정밀화 후보 | 21 | 21 | 28.425 | 45.059 | -3318.374 | 15 | 12 | 16 | reject |
| 포항시 | phase120_personal_business_sales_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 14 | 12 | 14.538 | 138.389 | -73238.326 | 11 | 7 | 12 | reject |
| 포항시 | phase120_personal_business_sales_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 14 | 11 | 14.538 | 138.639 | -73386.193 | 9 | 7 | 11 | reject |
| 포항시 | pbiz_fin_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 14 | 12 | 14.538 | 139.26 | -73753.403 | 10 | 7 | 12 | reject |
| 포항시 | pbiz_fin_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 14 | 10 | 14.538 | 139.826 | -74087.948 | 9 | 7 | 12 | reject |
| 포항시 | pbiz_fin_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 14 | 10 | 14.538 | 141.951 | -75344.396 | 10 | 7 | 12 | reject |
| 포항시 | pbiz_fin_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 14 | 10 | 14.538 | 141.951 | -75344.396 | 10 | 7 | 12 | reject |
| 포항시 | phase120_personal_business_profile_count_all | 개인사업자 기본정보 사업자 행수 | 검토 후보 | 14 | 13 | 14.538 | 142.086 | -75424.516 | 12 | 7 | 13 | reject |
| 포항시 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 개인사업자 절대 매출합계 | 정밀화 후보 | 14 | 12 | 14.538 | 142.123 | -75446.188 | 12 | 7 | 13 | reject |
| 포항시 | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 개인사업자 양수 매출합계 | 정밀화 후보 | 14 | 12 | 14.538 | 142.123 | -75446.188 | 12 | 7 | 13 | reject |
| 포항시 | pbiz_fin_abs_sale_all_vintage_unverified | 개인사업자 절대 매출합계 | 정밀화 후보 | 14 | 12 | 14.538 | 142.268 | -75532.31 | 12 | 7 | 13 | reject |
| 포항시 | pbiz_fin_positive_sale_all_vintage_unverified | 개인사업자 양수 매출합계 | 정밀화 후보 | 14 | 12 | 14.538 | 142.268 | -75532.31 | 12 | 7 | 13 | reject |
| 포항시 | pbiz_fin_asset_pos_lag2021 | 개인사업자 양수 자산합계 | 속보 후보 | 14 | 10 | 14.538 | 142.297 | -75549.133 | 10 | 7 | 12 | reject |
| 포항시 | pbiz_fin_asset_pos_all_vintage_unverified | 개인사업자 양수 자산합계 | 정밀화 후보 | 14 | 12 | 14.538 | 142.539 | -75692.476 | 12 | 7 | 13 | reject |
| 포항시 | pbiz_fin_profit_pos_lag2021 | 개인사업자 양수 영업이익합계 | 속보 후보 | 14 | 9 | 14.538 | 142.648 | -75756.581 | 9 | 7 | 12 | reject |
| 포항시 | phase120_personal_business_sales_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 14 | 11 | 14.538 | 142.994 | -75961.655 | 11 | 7 | 12 | reject |
| 포항시 | phase120_personal_business_sales_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 14 | 11 | 14.538 | 142.994 | -75961.655 | 11 | 7 | 12 | reject |
| 포항시 | pbiz_fin_profit_pos_all_vintage_unverified | 개인사업자 양수 영업이익합계 | 정밀화 후보 | 14 | 11 | 14.538 | 144.044 | -76582.599 | 11 | 7 | 13 | reject |
| 고양시 | mfg_va_2023 | 2023 제조업 중분류 부가가치 지표 | 누수위험 후보 | 21 | 20 | 28.425 | 40.138 | -2336.725 | 14 | 12 | 13 | reject_leakage_risk |
| 포항시 | mfg_va_2023 | 2023 제조업 중분류 부가가치 지표 | 누수위험 후보 | 14 | 14 | 14.538 | 30.199 | -9261.258 | 8 | 7 | 8 | reject_leakage_risk |

## 누수위험 후보

| 지역 | 후보ID | 지표 | 후보 WAPE(%) | 오차감소(억원) | 기각 사유 |
| --- | --- | --- | --- | --- | --- |
| 고양시 | mfg_va_2023 | 2023 제조업 중분류 부가가치 지표 | 40.138 | -2336.725 | 예측 대상과 너무 가까운 same-year lower-level value-added 지표이므로 운영 채택 금지 |
| 포항시 | mfg_va_2023 | 2023 제조업 중분류 부가가치 지표 | 30.199 | -9261.258 | 예측 대상과 너무 가까운 same-year lower-level value-added 지표이므로 운영 채택 금지 |

## 비누수 후보 상위

| 지역 | 후보ID | 지표 | 트랙 | 후보 WAPE(%) | 오차감소(억원) | 악화셀 | 판정 | 주의 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | pbiz_fin_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 31.677 | -648.793 | 12 | reject | 2023 예측시점에서 알 수 있었는지 미확인; 속보 사용 금지 |
| 고양시 | phase120_personal_business_sales_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 31.937 | -700.759 | 11 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | pbiz_fin_rows_lag2021 | 개인사업자 재무/매출 행수 | 속보 후보 | 32.415 | -796.142 | 10 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | phase120_personal_business_sales_rows_all_vintage_unverified | 개인사업자 재무/매출 행수 | 정밀화 후보 | 32.827 | -878.306 | 12 | reject | 2023 예측시점에서 알 수 있었는지 미확인; 속보 사용 금지 |
| 고양시 | phase120_personal_business_profile_count_all | 개인사업자 기본정보 사업자 행수 | 검토 후보 | 34.522 | -1216.439 | 14 | reject | 공표시점/정의 확인 필요 |
| 고양시 | pbiz_fin_asset_pos_lag2021 | 개인사업자 양수 자산합계 | 속보 후보 | 37.477 | -1805.907 | 12 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | pbiz_fin_profit_pos_lag2021 | 개인사업자 양수 영업이익합계 | 속보 후보 | 37.552 | -1820.804 | 12 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | pbiz_fin_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 37.855 | -1881.28 | 12 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | pbiz_fin_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 37.855 | -1881.28 | 12 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | pbiz_fin_profit_pos_all_vintage_unverified | 개인사업자 양수 영업이익합계 | 정밀화 후보 | 40.812 | -2471.19 | 14 | reject | 2023 예측시점에서 알 수 있었는지 미확인; 속보 사용 금지 |
| 고양시 | phase120_personal_business_sales_abs_sale_lag2021 | 개인사업자 절대 매출합계 | 속보 후보 | 41.359 | -2580.337 | 14 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |
| 고양시 | phase120_personal_business_sales_positive_sale_lag2021 | 개인사업자 양수 매출합계 | 속보 후보 | 41.359 | -2580.337 | 14 | reject | publication-lag 확인은 필요하지만 target-year actual 직접 사용 위험은 낮음 |

## C00 잔여 중분류별 필요자료

| 지역 | 중분류 | 오차(억원) | 오차율(%) | 필요 활동자료 |
| --- | --- | --- | --- | --- |
| 포항시 | 산업용 기계 및 장비 수리업 | 1286.21 | 255.23 | 수리업 사업장·정비계약·대형 설비 보유 사업장 자료 |
| 포항시 | 비금속 광물제품 제조업 | 857.09 | 22.42 | 공장규모·전력 + 지역 수요/건설·설비투자 보조 |
| 고양시 | 식료품 제조업 | 754.32 | 69.49 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 인쇄·기록매체 복제업 | 628.0 | 28.67 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 포항시 | 기타 기계 및 장비 제조업 | 577.38 | 48.81 | 공장규모·전력 + 지역 수요/건설·설비투자 보조 |
| 고양시 | 기타 제품 제조업 | 546.68 | 52.78 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 비금속 광물제품 제조업 | 525.53 | 45.55 | 공장규모·전력 + 지역 수요/건설·설비투자 보조 |
| 고양시 | 전자부품·컴퓨터 제조업 | 483.1 | 47.24 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 의복·모피 제조업 | 387.95 | 39.7 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 가구 제조업 | 384.04 | 62.74 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 가죽·가방·신발 제조업 | 232.85 | 40.71 | 공장등록 생산품·공장면적·종업원 + 산업용 전력 중분류 매핑 |
| 고양시 | 화학물질·화학제품 제조업 | 224.95 | 31.08 | 중분류별 생산품 매핑 + 전력/고용 결합 |

## 판정

1. 같은 해 시군구×중분류 제조업 부가가치 지표는 성능이 좋아도 채택하면 안 된다. 이는 우리가 예측하려는 target에 너무 가깝기 때문에 데이터 유출 위험이 크다.
2. 개인사업자 지연 구조자료(`lag2021`)는 속보 후보가 될 수 있으나, 제조업 전체 중분류를 안정적으로 개선하는지 여부는 외부 도시/상위 집계검증이 필요하다.
3. 현재 로컬 자료만으로는 C00 잔여 19개를 한 번에 10% 이내로 끌어내릴 안전한 후보가 확인되지 않았다.
4. 다음 개선은 자료 수집 없이도 가능한 “후보 만들기”와, 추가 API가 필요한 “직접 활동자료 보강”으로 나눠야 한다.
   - 즉시 가능: 공장등록 생산품/면적/종업원 + 전력 + 개인사업자 lag2021을 중분류별로 조합한 후보 생성.
   - 추가 필요: 산업용 기계 수리업의 정비계약·대형설비 보유 사업장, 비금속/기계장비의 프로젝트·설비투자 수요, 제조업 중분류별 지역 생산액의 공표시점 확인.

## 산출물

- 후보 상세: `data/processed/phase186_c00_indicator_screen/phase186_c00_indicator_screen_detail.csv`
- 후보 요약: `data/processed/phase186_c00_indicator_screen/phase186_c00_indicator_screen_summary.csv`
- 상위 후보 셀 변화: `data/processed/phase186_c00_indicator_screen/phase186_c00_top_candidate_cell_changes.csv`
