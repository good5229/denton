# Phase120 금융·조달 공개자료 통합 수집 및 GVA 후보실험

## 목적

활용신청이 완료된 조달청·금융공공데이터를 실제 고양시·포항시 중분류 총부가가치(GVA) 추정 실험에 연결한다. 이번 단계의 핵심은 “접속 확인”이 아니라, 무료 공개자료를 `지역 × KSIC 중분류` 활동자료로 바꿔 기존 속보/정밀화 오차 체계에 넣을 수 있는지 검증하는 것이다.

## 수집 완료 자료

| 지역 | 자료 | 행수 | 최소 기준년월 | 최대 기준년월 | 최소 재무기준연도 | 최대 재무기준연도 |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | profile | 31,013 | 202208 | 202506 |  |  |
| 고양시 | sales | 13,206 | 202208 | 202506 | 2002 | 2025 |
| 고양시 | finance | 8,299 | 202208 | 202506 | 2002 | 2024 |
| 포항시 | profile | 9,957 | 202208 | 202506 |  |  |
| 포항시 | sales | 3,952 | 202208 | 202506 | 2003 | 2025 |
| 포항시 | finance | 2,497 | 202208 | 202506 | 2003 | 2024 |


조달청 나라장터 입찰공고정보서비스는 HTTP 공공데이터포털 게이트웨이에서 정상 호출을 확인했다. 다만 날짜 외 지역 필터가 없어, 전국 공고 전량 수집 뒤 수요기관명·공고기관명으로 고양/포항을 걸러야 한다. API 응답이 느리고 이번 단계의 핵심 취약 업종에는 개인사업자 매출자료가 더 직접적이므로, 조달청은 배치 수집 후보로 남겼다.

보험가입정보와 금융회사재무신용정보도 정상 호출을 확인했다. 생명보험은 광역 지역 필드, 자동차보험은 전국 월별 계약·보험료 성격, 금융회사재무는 회사 단위 자료이므로 이번 중분류 공간배분에는 단독 투입하지 않았다.

## 개인사업자 자료의 집계 특성

| 지역 | 상위산업 | 지표 | 사용트랙 | 중분류 수 | 지표합계 |
| --- | --- | --- | --- | --- | --- |
| 고양시 | C00 | phase120_personal_business_finance_abs_sale_all_vintage_unverified | 정밀화 | 23 | 1,337,254,900,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_abs_sale_lag2021 | 속보성 | 21 | 692,323,900,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 정밀화 | 23 | 1,084,444,000,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_asset_pos_lag2021 | 속보성 | 21 | 441,700,400,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_positive_sale_all_vintage_unverified | 정밀화 | 23 | 1,337,254,900,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_positive_sale_lag2021 | 속보성 | 21 | 692,323,900,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_profit_pos_all_vintage_unverified | 정밀화 | 23 | 128,919,100,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_profit_pos_lag2021 | 속보성 | 21 | 64,578,000,000.0 |
| 고양시 | C00 | phase120_personal_business_finance_rows_all_vintage_unverified | 정밀화 | 23 | 1,747.0 |
| 고양시 | C00 | phase120_personal_business_finance_rows_lag2021 | 속보성 | 21 | 1,075.0 |
| 고양시 | C00 | phase120_personal_business_profile_count_all | 정밀화 | 24 | 3,218.0 |
| 고양시 | C00 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 정밀화 | 24 | 1,503,851,700,000.0 |
| 고양시 | C00 | phase120_personal_business_sales_abs_sale_lag2021 | 속보성 | 22 | 754,911,300,000.0 |
| 고양시 | C00 | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 정밀화 | 24 | 1,503,851,700,000.0 |
| 고양시 | C00 | phase120_personal_business_sales_positive_sale_lag2021 | 속보성 | 22 | 754,911,300,000.0 |
| 고양시 | C00 | phase120_personal_business_sales_rows_all_vintage_unverified | 정밀화 | 24 | 2,189.0 |
| 고양시 | C00 | phase120_personal_business_sales_rows_lag2021 | 속보성 | 22 | 1,259.0 |
| 고양시 | ERS | phase120_personal_business_finance_abs_sale_all_vintage_unverified | 정밀화 | 4 | 114,372,200,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_abs_sale_lag2021 | 속보성 | 4 | 54,717,800,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 정밀화 | 4 | 132,513,600,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_asset_pos_lag2021 | 속보성 | 4 | 42,216,800,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_positive_sale_all_vintage_unverified | 정밀화 | 4 | 114,372,200,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_positive_sale_lag2021 | 속보성 | 4 | 54,717,800,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_profit_pos_all_vintage_unverified | 정밀화 | 4 | 12,446,100,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_profit_pos_lag2021 | 속보성 | 4 | 5,419,100,000.0 |
| 고양시 | ERS | phase120_personal_business_finance_rows_all_vintage_unverified | 정밀화 | 4 | 226.0 |
| 고양시 | ERS | phase120_personal_business_finance_rows_lag2021 | 속보성 | 4 | 153.0 |
| 고양시 | ERS | phase120_personal_business_profile_count_all | 정밀화 | 5 | 2,591.0 |
| 고양시 | ERS | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 정밀화 | 5 | 146,292,400,000.0 |
| 고양시 | ERS | phase120_personal_business_sales_abs_sale_lag2021 | 속보성 | 5 | 65,093,300,000.0 |
| 고양시 | ERS | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 정밀화 | 5 | 146,292,400,000.0 |
| 고양시 | ERS | phase120_personal_business_sales_positive_sale_lag2021 | 속보성 | 5 | 65,093,300,000.0 |
| 고양시 | ERS | phase120_personal_business_sales_rows_all_vintage_unverified | 정밀화 | 5 | 866.0 |
| 고양시 | ERS | phase120_personal_business_sales_rows_lag2021 | 속보성 | 5 | 481.0 |
| 고양시 | F00 | phase120_personal_business_finance_abs_sale_all_vintage_unverified | 정밀화 | 2 | 193,984,400,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_abs_sale_lag2021 | 속보성 | 2 | 128,296,700,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 정밀화 | 2 | 90,545,000,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_asset_pos_lag2021 | 속보성 | 2 | 50,958,700,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_positive_sale_all_vintage_unverified | 정밀화 | 2 | 193,984,400,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_positive_sale_lag2021 | 속보성 | 2 | 128,296,700,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_profit_pos_all_vintage_unverified | 정밀화 | 2 | 15,506,800,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_profit_pos_lag2021 | 속보성 | 2 | 10,329,200,000.0 |
| 고양시 | F00 | phase120_personal_business_finance_rows_all_vintage_unverified | 정밀화 | 2 | 297.0 |
| 고양시 | F00 | phase120_personal_business_finance_rows_lag2021 | 속보성 | 2 | 210.0 |
| 고양시 | F00 | phase120_personal_business_profile_count_all | 정밀화 | 2 | 1,505.0 |
| 고양시 | F00 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 정밀화 | 2 | 218,391,200,000.0 |
| 고양시 | F00 | phase120_personal_business_sales_abs_sale_lag2021 | 속보성 | 2 | 138,473,100,000.0 |
| 고양시 | F00 | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 정밀화 | 2 | 218,391,200,000.0 |
| 고양시 | F00 | phase120_personal_business_sales_positive_sale_lag2021 | 속보성 | 2 | 138,473,100,000.0 |
| 고양시 | F00 | phase120_personal_business_sales_rows_all_vintage_unverified | 정밀화 | 2 | 741.0 |
| 고양시 | F00 | phase120_personal_business_sales_rows_lag2021 | 속보성 | 2 | 403.0 |
| 고양시 | G00 | phase120_personal_business_finance_abs_sale_all_vintage_unverified | 정밀화 | 3 | 4,259,676,399,872.0 |
| 고양시 | G00 | phase120_personal_business_finance_abs_sale_lag2021 | 속보성 | 3 | 2,662,098,899,872.0 |
| 고양시 | G00 | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 정밀화 | 3 | 1,939,901,400,000.0 |
| 고양시 | G00 | phase120_personal_business_finance_asset_pos_lag2021 | 속보성 | 3 | 1,096,006,700,000.0 |
| 고양시 | G00 | phase120_personal_business_finance_positive_sale_all_vintage_unverified | 정밀화 | 3 | 4,259,396,399,872.0 |
| 고양시 | G00 | phase120_personal_business_finance_positive_sale_lag2021 | 속보성 | 3 | 2,661,818,899,872.0 |
| 고양시 | G00 | phase120_personal_business_finance_profit_pos_all_vintage_unverified | 정밀화 | 3 | 257,204,800,000.0 |
| 고양시 | G00 | phase120_personal_business_finance_profit_pos_lag2021 | 속보성 | 3 | 162,960,700,000.0 |
| 고양시 | G00 | phase120_personal_business_finance_rows_all_vintage_unverified | 정밀화 | 3 | 4,479.0 |
| 고양시 | G00 | phase120_personal_business_finance_rows_lag2021 | 속보성 | 3 | 3,282.0 |
| 고양시 | G00 | phase120_personal_business_profile_count_all | 정밀화 | 3 | 12,558.0 |
| 고양시 | G00 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 정밀화 | 3 | 4,871,278,699,808.0 |
| 고양시 | G00 | phase120_personal_business_sales_abs_sale_lag2021 | 속보성 | 3 | 2,981,283,399,808.0 |
| 고양시 | G00 | phase120_personal_business_sales_positive_sale_all_vintage_unverified | 정밀화 | 3 | 4,870,998,699,808.0 |
| 고양시 | G00 | phase120_personal_business_sales_positive_sale_lag2021 | 속보성 | 3 | 2,981,003,399,808.0 |
| 고양시 | G00 | phase120_personal_business_sales_rows_all_vintage_unverified | 정밀화 | 3 | 5,967.0 |
| 고양시 | G00 | phase120_personal_business_sales_rows_lag2021 | 속보성 | 3 | 4,126.0 |
| 고양시 | H00 | phase120_personal_business_finance_abs_sale_all_vintage_unverified | 정밀화 | 2 | 119,338,100,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_abs_sale_lag2021 | 속보성 | 2 | 72,053,700,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 정밀화 | 2 | 55,428,300,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_asset_pos_lag2021 | 속보성 | 2 | 27,852,900,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_positive_sale_all_vintage_unverified | 정밀화 | 2 | 119,338,100,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_positive_sale_lag2021 | 속보성 | 2 | 72,053,700,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_profit_pos_all_vintage_unverified | 정밀화 | 2 | 8,595,200,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_profit_pos_lag2021 | 속보성 | 2 | 5,180,800,000.0 |
| 고양시 | H00 | phase120_personal_business_finance_rows_all_vintage_unverified | 정밀화 | 2 | 126.0 |
| 고양시 | H00 | phase120_personal_business_finance_rows_lag2021 | 속보성 | 2 | 90.00 |
| 고양시 | H00 | phase120_personal_business_profile_count_all | 정밀화 | 3 | 1,972.0 |
| 고양시 | H00 | phase120_personal_business_sales_abs_sale_all_vintage_unverified | 정밀화 | 2 | 142,875,800,000.0 |


주의: 개인사업자 매출자료에는 음수 매출이 존재한다. 따라서 이번 실험은 `양수 매출합계`, `절대 매출합계`, `행수`, `영업이익`, `자산`을 별도 후보로 두고, 후보 선택 과정에서 실제 GVA와 직접 맞추는 방식은 쓰지 않았다.

## 속보성 엄격 실험

`fnafBasYr<=2021`인 개인사업자 재무·매출 자료만 속보성 지연 구조자료로 허용했다. 현재 API의 과거 공표 빈티지가 로컬에 보존되어 있지 않기 때문에, 2022년 이후 기준자료는 속보성 성능값에 넣지 않았다.

| 지역 | 실제합계 억원 | 기준오차 억원 | 기준오차 % | Phase120 오차 억원 | Phase120 오차 % | 감소 억원 | 감소 pp | 기준 20%초과 | Phase120 20%초과 | 기준 10%초과 | Phase120 10%초과 | 악화 셀 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 고양시 | 169,395.1 | 74,685.3 | 44.09 | 26,951.6 | 15.91 | 47,733.7 | 28.18 | 42 | 29 | 50 | 41 | 17 |
| 포항시 | 154,484.8 | 113,474.8 | 73.45 | 34,590.0 | 22.39 | 78,884.8 | 51.06 | 46 | 30 | 49 | 35 | 11 |


### 속보성 채택 후보

| 지역 | 상위산업 | 선택 지표 | 혼합비 | 기존구조 보존비 | 기준오차 억원 | 후보오차 억원 | 감소 억원 | 기준 20%초과 | 후보 20%초과 | 판정 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 포항시 | C00 | flash_kosis_mfg_2021_value_added | 1.00 | 0.00 | 57,472.1 | 8,596.9 | 48,875.3 | 12 | 7 | 속보 후보: 검증 통과 |
| 고양시 | G00 | phase120_personal_business_sales_rows_lag2021 | 0.50 | 0.05 | 10,887.6 | 2,466.3 | 8,421.2 | 3 | 0 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | G00 | phase120_personal_business_sales_abs_sale_lag2021 | 0.67 | 0.00 | 4,017.6 | 28.71 | 3,988.9 | 3 | 0 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | F00 | flash_building_start_area_ytd | 0.50 | 0.00 | 14,079.7 | 474.5 | 13,605.2 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | Q00 | flash_localdata_Q00_86_active_area | 0.67 | 0.00 | 13,825.4 | 228.2 | 13,597.2 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | H00 | flash_localdata_H52_logistics_warehouse_capacity | 0.67 | 0.40 | 13,250.2 | 539.4 | 12,710.8 | 3 | 1 | 속보 후보: 검증 통과 |
| 고양시 | F00 | flash_building_start_area_ytd | 0.50 | 0.20 | 10,144.9 | 1.50 | 10,143.4 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | Q00 | flash_localdata_Q00_86_active_area | 0.67 | 0.05 | 6,352.6 | 24.13 | 6,328.5 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | H00 | flash_localdata_H52_logistics_warehouse_capacity | 0.20 | 0.10 | 4,680.9 | 1,148.4 | 3,532.4 | 3 | 1 | 속보 후보: 검증 통과 |
| 포항시 | A00 | flash_agri_2015_small_sales_middle | 1.00 | 0.00 | 1,922.9 | 0.00 | 1,922.9 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | ERS | flash_localdata_ERS_91_active_area | 0.25 | 0.40 | 7,546.8 | 5,475.9 | 2,071.0 | 7 | 6 | 속보 후보: 검증 통과 |
| 고양시 | C00 | flash_kosis_mfg_2021_value_added | 0.15 | 0.60 | 5,999.7 | 5,670.5 | 329.2 | 13 | 12 | 속보 후보: 검증 통과 |
| 고양시 | MN0 | phase120_personal_business_sales_rows_lag2021 | 0.08 | 0.20 | 4,263.9 | 3,975.0 | 288.9 | 4 | 3 | 속보 후보: 2021 이하 지연자료 |
| 고양시 | I00 | flash_고양시_I00_localdata_bundle | 0.03 | 0.10 | 172.8 | 0.70 | 172.1 | 1 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | MN0 | phase120_personal_business_finance_rows_lag2021 | 0.05 | 0.10 | 13,877.2 | 13,598.3 | 278.9 | 7 | 7 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | ERS | phase120_personal_business_finance_abs_sale_lag2021 | 0.05 | 0.40 | 4,897.9 | 4,693.8 | 204.1 | 6 | 6 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | I00 | phase120_personal_business_finance_asset_pos_lag2021 | 0.20 | 0.10 | 150.3 | 1.70 | 148.6 | 0 | 0 | 속보 후보: 2021 이하 지연자료 |


## 정밀화 후보 포함 실험

아래는 현재 API 전체 자료를 정밀화 후보까지 포함해 평가한 결과다. 이 값은 “현 시점에서 더 정밀하게 재배분할 가능성”을 보는 것이며, 예측시점 당시 사용할 수 있었다고 주장하려면 공표시점·빈티지 검사가 추가로 필요하다.

| 지역 | 실제합계 억원 | 기준오차 억원 | 기준오차 % | Phase120 후보오차 억원 | Phase120 후보오차 % | 감소 억원 | 감소 pp | 기준 20%초과 | 후보 20%초과 | 기준 10%초과 | 후보 10%초과 | 악화 셀 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 고양시 | 169,395.1 | 74,685.3 | 44.09 | 26,951.6 | 15.91 | 47,733.7 | 28.18 | 42 | 29 | 50 | 41 | 17 |
| 포항시 | 154,484.8 | 113,474.8 | 73.45 | 34,578.5 | 22.38 | 78,896.3 | 51.07 | 46 | 30 | 49 | 35 | 10 |


### 정밀화 후보 채택 지표

| 지역 | 상위산업 | 선택 지표 | 혼합비 | 기존구조 보존비 | 기준오차 억원 | 후보오차 억원 | 감소 억원 | 기준 20%초과 | 후보 20%초과 | 판정 |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 포항시 | C00 | flash_kosis_mfg_2021_value_added | 1.00 | 0.00 | 57,472.1 | 8,596.9 | 48,875.3 | 12 | 7 | 속보 후보: 검증 통과 |
| 고양시 | G00 | phase120_personal_business_sales_rows_lag2021 | 0.50 | 0.05 | 10,887.6 | 2,466.3 | 8,421.2 | 3 | 0 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | G00 | phase120_personal_business_sales_abs_sale_lag2021 | 0.67 | 0.00 | 4,017.6 | 28.71 | 3,988.9 | 3 | 0 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | F00 | flash_building_start_area_ytd | 0.50 | 0.00 | 14,079.7 | 474.5 | 13,605.2 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | Q00 | flash_localdata_Q00_86_active_area | 0.67 | 0.00 | 13,825.4 | 228.2 | 13,597.2 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | H00 | flash_localdata_H52_logistics_warehouse_capacity | 0.67 | 0.40 | 13,250.2 | 539.4 | 12,710.8 | 3 | 1 | 속보 후보: 검증 통과 |
| 고양시 | F00 | flash_building_start_area_ytd | 0.50 | 0.20 | 10,144.9 | 1.50 | 10,143.4 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | Q00 | flash_localdata_Q00_86_active_area | 0.67 | 0.05 | 6,352.6 | 24.13 | 6,328.5 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | H00 | flash_localdata_H52_logistics_warehouse_capacity | 0.20 | 0.10 | 4,680.9 | 1,148.4 | 3,532.4 | 3 | 1 | 속보 후보: 검증 통과 |
| 포항시 | A00 | flash_agri_2015_small_sales_middle | 1.00 | 0.00 | 1,922.9 | 0.00 | 1,922.9 | 2 | 0 | 보류: 2셀 고적합 후보 |
| 고양시 | ERS | flash_localdata_ERS_91_active_area | 0.25 | 0.40 | 7,546.8 | 5,475.9 | 2,071.0 | 7 | 6 | 속보 후보: 검증 통과 |
| 고양시 | C00 | flash_kosis_mfg_2021_value_added | 0.15 | 0.60 | 5,999.7 | 5,670.5 | 329.2 | 13 | 12 | 속보 후보: 검증 통과 |
| 고양시 | MN0 | phase120_personal_business_sales_rows_lag2021 | 0.08 | 0.20 | 4,263.9 | 3,975.0 | 288.9 | 4 | 3 | 속보 후보: 2021 이하 지연자료 |
| 고양시 | I00 | flash_고양시_I00_localdata_bundle | 0.03 | 0.10 | 172.8 | 0.70 | 172.1 | 1 | 0 | 보류: 2셀 고적합 후보 |
| 포항시 | MN0 | phase120_personal_business_finance_rows_lag2021 | 0.05 | 0.10 | 13,877.2 | 13,598.3 | 278.9 | 7 | 7 | 속보 후보: 2021 이하 지연자료 |
| 포항시 | ERS | phase120_personal_business_finance_asset_pos_all_vintage_unverified | 0.05 | 0.20 | 4,897.9 | 4,682.7 | 215.2 | 6 | 6 | 정밀화 후보: API 빈티지 확인 필요 |
| 포항시 | I00 | phase120_personal_business_finance_rows_all_vintage_unverified | 1.00 | 0.05 | 150.3 | 1.31 | 149.0 | 0 | 0 | 정밀화 후보: API 빈티지 확인 필요 |


## 개선된 중분류

| 지역 | 상위산업 | 코드 | 중분류 | 실제 억원 | 기준오차 억원 | 후보오차 억원 | 후보오차 % | 감소 억원 | 적용 지표 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 고양시 | Q00 | 87 | 사회복지 서비스업 | 3,234.5 | 6,912.7 | 114.1 | 3.53 | 6,798.6 | flash_localdata_Q00_86_active_area |
| 고양시 | Q00 | 86 | 보건업 | 19,561.5 | 6,912.7 | 114.1 | 0.58 | 6,798.6 | flash_localdata_Q00_86_active_area |
| 고양시 | H00 | 52 | 창고·운송관련 서비스업 | 9,201.4 | 6,606.0 | 243.8 | 2.65 | 6,362.1 | flash_localdata_H52_logistics_warehouse_capacity |
| 고양시 | H00 | 49 | 육상운송업 | 9,184.3 | 6,625.1 | 269.7 | 2.94 | 6,355.4 | flash_localdata_H52_logistics_warehouse_capacity |
| 고양시 | F00 | 41 | 종합 건설업 | 8,445.3 | 5,072.5 | 0.75 | 0.01 | 5,071.7 | flash_building_start_area_ytd |
| 고양시 | F00 | 42 | 전문직별 공사업 | 7,606.8 | 5,072.5 | 0.75 | 0.01 | 5,071.7 | flash_building_start_area_ytd |
| 고양시 | G00 | 47 | 소매업 | 12,778.7 | 5,443.8 | 811.3 | 6.35 | 4,632.5 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | G00 | 46 | 도매·상품중개업 | 16,007.7 | 4,364.7 | 1,233.2 | 7.70 | 3,131.6 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | ERS | 91 | 스포츠·오락 서비스업 | 4,365.6 | 1,614.2 | 49.01 | 1.12 | 1,565.2 | flash_localdata_ERS_91_active_area |
| 고양시 | ERS | 96 | 기타 개인 서비스업 | 2,465.5 | 2,688.8 | 1,915.7 | 77.70 | 773.2 | flash_localdata_ERS_91_active_area |
| 고양시 | G00 | 45 | 자동차·부품 판매업 | 2,304.8 | 1,079.0 | 421.9 | 18.30 | 657.1 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | ERS | 94 | 협회·단체 | 991.0 | 1,084.6 | 773.3 | 78.03 | 311.3 | flash_localdata_ERS_91_active_area |
| 고양시 | MN0 | 75 | 사업지원 서비스업 | 4,277.0 | 1,135.5 | 836.8 | 19.56 | 298.8 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | MN0 | 71 | 전문 서비스업 | 4,106.1 | 384.0 | 205.5 | 5.01 | 178.5 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | C00 | 27 | 의료·정밀기기 제조업 | 1,147.3 | 287.7 | 180.6 | 15.74 | 107.1 | flash_kosis_mfg_2021_value_added |
| 고양시 | I00 | 55 | 숙박업 | 320.8 | 86.39 | 0.35 | 0.11 | 86.04 | flash_고양시_I00_localdata_bundle |
| 고양시 | I00 | 56 | 음식점·주점업 | 7,760.5 | 86.39 | 0.35 | 0.00 | 86.04 | flash_고양시_I00_localdata_bundle |
| 고양시 | MN0 | 74 | 사업시설 관리업 | 1,389.4 | 377.7 | 292.4 | 21.04 | 85.31 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | C00 | 23 | 비금속 광물제품 제조업 | 1,153.9 | 599.8 | 525.5 | 45.55 | 74.24 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 33 | 기타 제품 제조업 | 1,035.8 | 610.0 | 546.7 | 52.78 | 63.30 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 32 | 가구 제조업 | 612.1 | 427.4 | 384.0 | 62.74 | 43.37 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 25 | 금속가공제품 제조업 | 1,295.9 | 287.2 | 246.2 | 19.00 | 41.07 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 18 | 인쇄·기록매체 복제업 | 2,190.7 | 657.6 | 628.0 | 28.67 | 29.65 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 34 | 산업용 기계 수리업 | 388.2 | 55.42 | 28.81 | 7.42 | 26.61 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 28 | 전기장비 제조업 | 1,848.9 | 294.2 | 268.5 | 14.52 | 25.66 | flash_kosis_mfg_2021_value_added |
| 고양시 | MN0 | 76 | 임대업 | 1,610.2 | 82.07 | 64.78 | 4.02 | 17.28 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | C00 | 26 | 전자부품·컴퓨터 제조업 | 1,022.8 | 497.9 | 483.1 | 47.24 | 14.76 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 17 | 펄프·종이 제조업 | 1,721.0 | 33.87 | 22.80 | 1.32 | 11.07 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 29 | 기계·장비 제조업 | 1,257.7 | 49.76 | 42.73 | 3.40 | 7.03 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 30 | 자동차·트레일러 제조업 | 159.8 | 31.01 | 26.68 | 16.69 | 4.33 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 16 | 목재·나무제품 제조업 | 205.9 | 192.9 | 191.5 | 92.98 | 1.41 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 24 | 1차 금속 제조업 | 47,010.5 | 31,236.8 | 4,653.5 | 9.90 | 26,583.2 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 10 | 식료품 제조업 | 525.7 | 9,100.4 | 45.00 | 8.56 | 9,055.4 | flash_kosis_mfg_2021_value_added |
| 포항시 | F00 | 41 | 종합 건설업 | 12,603.4 | 7,039.8 | 237.2 | 1.88 | 6,802.6 | flash_building_start_area_ytd |
| 포항시 | F00 | 42 | 전문직별 공사업 | 6,565.3 | 7,039.8 | 237.2 | 3.61 | 6,802.6 | flash_building_start_area_ytd |
| 포항시 | C00 | 25 | 금속가공제품 제조업; 기계 및 가구 제외 | 2,736.2 | 5,140.3 | 524.5 | 19.17 | 4,615.8 | flash_kosis_mfg_2021_value_added |
| 포항시 | Q00 | 86 | 보건업 | 8,754.9 | 3,176.3 | 12.06 | 0.14 | 3,164.2 | flash_localdata_Q00_86_active_area |
| 포항시 | Q00 | 87 | 사회복지 서비스업 | 1,795.0 | 3,176.3 | 12.06 | 0.67 | 3,164.2 | flash_localdata_Q00_86_active_area |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.9 | 4,175.6 | 1,286.2 | 255.2 | 2,889.4 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 29 | 기타 기계 및 장비 제조업 | 1,182.9 | 3,298.4 | 577.4 | 48.81 | 2,721.0 | flash_kosis_mfg_2021_value_added |
| 포항시 | G00 | 47 | 소매업; 자동차 제외 | 3,930.2 | 2,008.8 | 11.17 | 0.28 | 1,997.6 | phase120_personal_business_sales_abs_sale_lag2021 |
| 포항시 | H00 | 49 | 육상운송 및 파이프라인 운송업 | 8,165.3 | 2,340.4 | 449.4 | 5.50 | 1,891.0 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | H00 | 52 | 창고 및 운송관련 서비스업 | 3,922.7 | 1,848.4 | 124.8 | 3.18 | 1,723.6 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | G00 | 46 | 도매 및 상품 중개업 | 4,102.3 | 1,696.9 | 14.35 | 0.35 | 1,682.5 | phase120_personal_business_sales_abs_sale_lag2021 |
| 포항시 | C00 | 28 | 전기장비 제조업 | 971.7 | 1,387.5 | 112.1 | 11.54 | 1,275.3 | flash_kosis_mfg_2021_value_added |
| 포항시 | A00 | 02 | 임업 | 170.9 | 961.4 | 0.00 | 0.00 | 961.4 | flash_agri_2015_small_sales_middle |
| 포항시 | A00 | 01 | 농업 | 2,206.2 | 961.4 | 0.00 | 0.00 | 961.4 | flash_agri_2015_small_sales_middle |
| 포항시 | C00 | 27 | 의료 정밀 광학기기 및 시계 제조업 | 183.8 | 838.5 | 143.2 | 77.93 | 695.3 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 22 | 고무 및 플라스틱제품 제조업 | 101.9 | 566.4 | 6.15 | 6.03 | 560.2 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 16 | 목재 및 나무제품 제조업; 가구 제외 | 60.44 | 509.1 | 8.38 | 13.86 | 500.7 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 31 | 기타 운송장비 제조업 | 255.8 | 439.0 | 92.65 | 36.22 | 346.3 | flash_kosis_mfg_2021_value_added |
| 포항시 | G00 | 45 | 자동차 및 부품 판매업 | 628.2 | 311.9 | 3.19 | 0.51 | 308.7 | phase120_personal_business_sales_abs_sale_lag2021 |
| 포항시 | MN0 | 75 | 사업지원 서비스업 | 2,693.3 | 2,979.6 | 2,724.3 | 101.2 | 255.3 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.5 | 315.3 | 96.47 | 92.29 | 218.8 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 17 | 펄프 종이 및 종이제품 제조업 | 96.15 | 265.0 | 50.36 | 52.38 | 214.6 | flash_kosis_mfg_2021_value_added |
| 포항시 | MN0 | 71 | 전문 서비스업 | 8,943.0 | 6,195.5 | 6,015.6 | 67.27 | 180.0 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | ERS | 95 | 개인 및 소비용품 수리업 | 1,347.5 | 120.6 | 15.81 | 1.17 | 104.8 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | ERS | 96 | 기타 개인 서비스업 | 910.7 | 1,803.3 | 1,727.8 | 189.7 | 75.50 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | I00 | 56 | 음식점 및 주점업 | 5,200.9 | 75.17 | 0.66 | 0.01 | 74.52 | phase120_personal_business_finance_rows_all_vintage_unverified |
| 포항시 | I00 | 55 | 숙박업 | 448.7 | 75.17 | 0.66 | 0.15 | 74.52 | phase120_personal_business_finance_rows_all_vintage_unverified |
| 포항시 | MN0 | 74 | 사업시설 관리 및 조경 서비스업 | 1,421.3 | 1,044.2 | 983.8 | 69.22 | 60.35 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | ERS | 94 | 협회 및 단체 | 519.1 | 459.3 | 420.2 | 80.94 | 39.14 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | ERS | 91 | 스포츠 및 오락관련 서비스업 | 971.9 | 186.4 | 177.6 | 18.27 | 8.80 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.3 | 1,032.5 | 1,023.7 | 40.38 | 8.75 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | ERS | 90 | 창작 예술 및 여가관련 서비스업 | 174.9 | 24.52 | 18.79 | 10.74 | 5.73 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |


## 남은 20% 초과 중분류

| 지역 | 상위산업 | 코드 | 중분류 | 실제 억원 | 후보추정 억원 | 오차 억원 | 오차 % | 적용 지표 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 고양시 | ERS | 96 | 기타 개인 서비스업 | 2,465.5 | 4,381.2 | 1,915.7 | 77.70 | flash_localdata_ERS_91_active_area |
| 고양시 | K00 | 66 | 금융·보험 관련 서비스업 | 1,473.9 | 3,257.3 | 1,783.4 | 121.0 | baseline |
| 고양시 | J00 | 61 | 우편·통신업 | 3,000.5 | 1,232.9 | 1,767.6 | 58.91 | baseline |
| 고양시 | MN0 | 70 | 연구개발업 | 1,920.2 | 514.8 | 1,405.4 | 73.19 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | J00 | 58 | 출판업 | 2,524.2 | 3,776.7 | 1,252.5 | 49.62 | baseline |
| 고양시 | ERS | 38 | 폐기물 처리·재생업 | 1,408.7 | 300.1 | 1,108.5 | 78.70 | flash_localdata_ERS_91_active_area |
| 고양시 | MN0 | 73 | 과학기술 서비스업 | 969.0 | 1,827.4 | 858.4 | 88.59 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | ERS | 94 | 협회·단체 | 991.0 | 1,764.2 | 773.3 | 78.03 | flash_localdata_ERS_91_active_area |
| 고양시 | C00 | 10 | 식료품 제조업 | 1,085.5 | 1,839.8 | 754.3 | 69.49 | flash_kosis_mfg_2021_value_added |
| 고양시 | J00 | 60 | 방송업 | 954.7 | 208.7 | 746.0 | 78.14 | baseline |
| 고양시 | C00 | 18 | 인쇄·기록매체 복제업 | 2,190.7 | 2,818.7 | 628.0 | 28.67 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 33 | 기타 제품 제조업 | 1,035.8 | 1,582.5 | 546.7 | 52.78 | flash_kosis_mfg_2021_value_added |
| 고양시 | J00 | 62 | 컴퓨터·시스템통합업 | 750.5 | 1,297.0 | 546.4 | 72.81 | baseline |
| 고양시 | ERS | 90 | 창작·예술 서비스업 | 1,141.9 | 598.9 | 543.0 | 47.55 | flash_localdata_ERS_91_active_area |
| 고양시 | C00 | 23 | 비금속 광물제품 제조업 | 1,153.9 | 628.3 | 525.5 | 45.55 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 26 | 전자부품·컴퓨터 제조업 | 1,022.8 | 539.7 | 483.1 | 47.24 | flash_kosis_mfg_2021_value_added |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.0 | 1,870.5 | 403.5 | 27.50 | baseline |
| 고양시 | C00 | 14 | 의복·모피 제조업 | 977.2 | 589.3 | 388.0 | 39.70 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 32 | 가구 제조업 | 612.1 | 996.2 | 384.0 | 62.74 | flash_kosis_mfg_2021_value_added |
| 고양시 | ERS | 37 | 하수·폐수 처리업 | 444.9 | 92.71 | 352.2 | 79.16 | flash_localdata_ERS_91_active_area |
| 고양시 | ERS | 36 | 수도업 | 377.3 | 49.85 | 327.5 | 86.79 | flash_localdata_ERS_91_active_area |
| 고양시 | J00 | 63 | 정보서비스업 | 225.9 | 537.2 | 311.3 | 137.8 | baseline |
| 고양시 | MN0 | 74 | 사업시설 관리업 | 1,389.4 | 1,681.8 | 292.4 | 21.04 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | C00 | 15 | 가죽·가방·신발 제조업 | 572.0 | 339.2 | 232.9 | 40.71 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 20 | 화학물질·화학제품 제조업 | 723.8 | 498.8 | 225.0 | 31.08 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 16 | 목재·나무제품 제조업 | 205.9 | 397.4 | 191.5 | 92.98 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 13 | 섬유제품 제조업 | 786.6 | 622.6 | 164.0 | 20.85 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 21 | 의약품 제조업 | 69.97 | 115.9 | 45.96 | 65.68 | flash_kosis_mfg_2021_value_added |
| 고양시 | H00 | 50 | 수상 운송업 | 35.94 | 10.05 | 25.90 | 72.05 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | MN0 | 71 | 전문 서비스업 | 8,943.0 | 2,927.4 | 6,015.6 | 67.27 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | MN0 | 75 | 사업지원 서비스업 | 2,693.3 | 5,417.6 | 2,724.3 | 101.2 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | K00 | 65 | 보험 및 연금업 | 4,807.5 | 2,870.9 | 1,936.7 | 40.28 | baseline |
| 포항시 | ERS | 96 | 기타 개인 서비스업 | 910.7 | 2,638.4 | 1,727.8 | 189.7 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | ERS | 38 | 폐기물 수집 운반 처리 및 원료 재생업 | 2,001.0 | 304.4 | 1,696.6 | 84.79 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.9 | 1,790.1 | 1,286.2 | 255.2 | flash_kosis_mfg_2021_value_added |
| 포항시 | MN0 | 76 | 임대업; 부동산 제외 | 635.2 | 1,735.6 | 1,100.4 | 173.2 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.3 | 3,559.0 | 1,023.7 | 40.38 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | K00 | 64 | 금융업 | 2,788.7 | 3,802.3 | 1,013.5 | 36.34 | baseline |
| 포항시 | MN0 | 74 | 사업시설 관리 및 조경 서비스업 | 1,421.3 | 2,405.1 | 983.8 | 69.22 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | MN0 | 73 | 기타 전문 과학 및 기술 서비스업 | 120.1 | 1,087.0 | 966.9 | 805.4 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | J00 | 61 | 우편 및 통신업 | 1,816.8 | 862.3 | 954.5 | 52.54 | baseline |
| 포항시 | K00 | 66 | 금융 및 보험 관련 서비스업 | 859.1 | 1,782.3 | 923.1 | 107.4 | baseline |
| 포항시 | C00 | 23 | 비금속 광물제품 제조업 | 3,822.9 | 2,965.8 | 857.1 | 22.42 | flash_kosis_mfg_2021_value_added |
| 포항시 | MN0 | 70 | 연구개발업 | 1,642.9 | 859.3 | 783.6 | 47.69 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | C00 | 29 | 기타 기계 및 장비 제조업 | 1,182.9 | 605.5 | 577.4 | 48.81 | flash_kosis_mfg_2021_value_added |
| 포항시 | H00 | 50 | 수상 운송업 | 948.6 | 374.4 | 574.2 | 60.53 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | J00 | 58 | 출판업 | 224.1 | 768.3 | 544.3 | 242.9 | baseline |
| 포항시 | ERS | 94 | 협회 및 단체 | 519.1 | 939.2 | 420.2 | 80.94 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | ERS | 36 | 수도업 | 439.7 | 52.84 | 386.9 | 87.98 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | J00 | 62 | 컴퓨터 프로그래밍 시스템 통합 및 관리업 | 194.6 | 567.4 | 372.8 | 191.5 | baseline |
| 포항시 | ERS | 37 | 하수 폐수 및 분뇨 처리업 | 296.0 | 81.31 | 214.7 | 72.53 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |
| 포항시 | C00 | 27 | 의료 정밀 광학기기 및 시계 제조업 | 183.8 | 327.0 | 143.2 | 77.93 | flash_kosis_mfg_2021_value_added |
| 포항시 | J00 | 60 | 방송업 | 386.8 | 266.2 | 120.6 | 31.19 | baseline |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.5 | 201.0 | 96.47 | 92.29 | flash_kosis_mfg_2021_value_added |
| 포항시 | C00 | 31 | 기타 운송장비 제조업 | 255.8 | 163.1 | 92.65 | 36.22 | flash_kosis_mfg_2021_value_added |
| 포항시 | J00 | 59 | 영상ㆍ오디오 기록물 제작 및 배급업 | 139.8 | 230.7 | 90.96 | 65.08 | baseline |
| 포항시 | J00 | 63 | 정보서비스업 | 3.95 | 71.05 | 67.10 | 1,700.5 | baseline |
| 포항시 | C00 | 17 | 펄프 종이 및 종이제품 제조업 | 96.15 | 45.79 | 50.36 | 52.38 | flash_kosis_mfg_2021_value_added |
| 포항시 | ERS | 39 | 환경 정화 및 복원업 | 34.85 | 10.54 | 24.31 | 69.76 | phase120_personal_business_finance_asset_pos_all_vintage_unverified |


## 판정

1. 원하는 공개 API의 접속은 사실상 완료됐다. 추가 API key 요청은 현재 없다.
2. 모델에 바로 강하게 들어갈 수 있는 자료는 개인사업자 재무·매출이다. 조달청은 전문서비스·건설의 속보성 보조자료지만, 지역 필터가 없어 별도 배치 수집 설계가 필요하다.
3. 개인사업자 자료는 고양·포항의 도소매·숙박음식·운수·전문서비스·개인서비스 계열을 직접 보강할 수 있다. 다만 현재 API 빈티지라 정밀화 후보와 속보성 후보를 분리해야 한다.
4. 보험·금융회사 API는 K00 금융보험업 보조자료로 유효하지만, 시군구 중분류 GVA 공간배분의 단독 근거로 쓰기에는 지역 해상도가 부족하다.
