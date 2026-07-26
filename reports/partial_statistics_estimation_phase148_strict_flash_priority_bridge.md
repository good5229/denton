# Phase148 strict flash 전용 우선순위 브릿지 감사

## 목적

Phase147은 금액가중 관점에서 중분류 개선 우선순위를 정했다. 이번 Phase148은 그 우선순위 업종들에 대해 **strict/as-of 적격 후보(속보 활동지표 또는 lagged 구조자료)가 이미 있는지**를 점검한다.

중요한 전제는 다음과 같다.

- Phase145/147의 rolling 성능은 2022~2023 기간의 분기별 nowcast 운영 벤치마크다.
- Phase120 strict/as-of 후보는 2023 단면에서 속보성 또는 지연 구조자료 후보를 붙인 cross-sectional 감사다. 일부 후보는 `보류`, `2021 이하 지연자료`, `공표일자 확인 필요` 상태이므로 strict 확정 자료로 읽으면 안 된다.
- 따라서 Phase120 수치를 Phase145 WAPE와 직접 비교해 “성능이 개선됐다”고 주장하지 않는다. 이번 결과는 **strict flash 보강 가능성 지도**로만 사용한다.

## Phase120 2023 단면 후보 적합도(운영 개선 아님)

| 지역 | 2023 실제합계(억원) | 기준오차(억원) | 기준 WAPE(%) | 후보오차(억원) | 후보 WAPE(%) | 2023 단면 기준오차 대비 차이(억원) | 2023 단면 WAPE 차이(%p) | 기준 20%초과 | strict 20%초과 | 기준 10%초과 | strict 10%초과 | 악화셀 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 169,395.14 | 74,685.32 | 44.09 | 26,951.63 | 15.91 | 47,733.69 | 28.18 | 42 | 29 | 50 | 41 | 17 |
| 포항시 | 154,484.79 | 113,474.76 | 73.45 | 34,589.97 | 22.39 | 78,884.78 | 51.06 | 46 | 30 | 49 | 35 | 11 |

이 표는 2023 단면의 후보 성능이다. Phase145의 2022~2023 rolling WAPE와 같은 평가가 아니므로, 포스터/보고서에서 운영 성능으로 승격하면 안 된다.

## 금액가중 우선순위와 strict/as-of 후보 연결 요약

조인 감사: Phase147 Q1 우선순위 중분류 43개 중 Phase120 후보 미매칭은 9개, 상위그룹 불일치는 0개다. 미매칭 업종은 **직접 as-of 후보 없음**으로 분류했다.

| 지역 | 후보상태 | 중분류 수 | rolling 실제합계(억원) | rolling 오차합(억원) | 전체 Q1 rolling 실제비중(%) | 전체 Q1 rolling 오차기여(%) |
| --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 2023 단면 저오차·검증통과 | 1 | 13,436.93 | 379.26 | 2.93 | 1.61 |
| 고양시 | 2023 단면 저오차이나 보류 | 5 | 86,896.93 | 3,694.56 | 18.96 | 15.73 |
| 고양시 | 2023 단면 저오차이나 운영개선필요 | 1 | 8,087.69 | 620.81 | 1.76 | 2.64 |
| 고양시 | 2023 단면 취약 | 1 | 5,744.00 | 777.39 | 1.25 | 3.31 |
| 고양시 | baseline 유지 | 3 | 26,907.57 | 1,567.23 | 5.87 | 6.67 |
| 고양시 | 운영개선필요 후보 | 1 | 3,662.60 | 495.69 | 0.80 | 2.11 |
| 고양시 | 지연 구조자료 후보 | 3 | 63,674.26 | 2,261.27 | 13.90 | 9.63 |
| 고양시 | 직접 as-of 후보 없음 | 4 | 127,489.88 | 5,375.82 | 27.82 | 22.89 |
| 포항시 | 2023 단면 저오차·검증통과 | 3 | 34,515.87 | 1,131.27 | 9.32 | 7.81 |
| 포항시 | 2023 단면 저오차이나 보류 | 4 | 56,326.22 | 1,449.06 | 15.20 | 10.01 |
| 포항시 | 2023 단면 저오차이나 운영개선필요 | 1 | 30,595.14 | 820.18 | 8.26 | 5.66 |
| 포항시 | 2023 단면 주의 | 1 | 15,277.42 | 409.55 | 4.12 | 2.83 |
| 포항시 | 2023 단면 취약 | 2 | 11,041.90 | 556.31 | 2.98 | 3.84 |
| 포항시 | baseline 유지 | 1 | 6,690.16 | 409.45 | 1.81 | 2.83 |
| 포항시 | 운영개선필요 후보 | 1 | 9,076.48 | 243.32 | 2.45 | 1.68 |
| 포항시 | 지연 구조자료 후보 | 6 | 37,587.18 | 2,754.04 | 10.14 | 19.02 |
| 포항시 | 직접 as-of 후보 없음 | 5 | 81,851.77 | 3,837.48 | 22.09 | 26.50 |

## 고양시 Q1 우선순위 브릿지(상위 15개 표시, 전체는 CSV 참조)

| 지역 | 중분류 | 업종명 | 금액가중 등급 | rolling 실제(억원) | rolling 오차(억원) | rolling WAPE(%) | rolling 오차기여(%) | 2023 후보 | 2023 후보 오차율(%) | 2023 후보 오차(억원) | 후보트랙 | Phase120 공개판정 | 상위그룹 일치 | 판정 | 다음 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 68 | 부동산업 | 핵심개선 | 57,593.37 | 3,611.30 | 6.27 | 15.38 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 국토부 실거래·공시가격·건축물 공표시점 확인 후 strict 후보 생성 |
| 고양시 | 47 | 소매업; 자동차 제외 | 핵심개선 | 33,614.72 | 1,141.98 | 3.40 | 4.86 | phase120_personal_business_sales_rows_lag2021 | 6.35 | 811.28 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 고양시 | 42 | 전문직별 공사업 | 핵심개선 | 26,028.23 | 1,005.42 | 3.86 | 4.28 | flash_building_start_area_ytd | 0.01 | 0.75 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 56 | 음식점 및 주점업 | 관리관찰 | 10,645.55 | 1,053.31 | 9.89 | 4.48 | flash_고양시_I00_localdata_bundle | 0.00 | 0.35 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 85 | 교육 서비스업 | 관리관찰 | 31,051.10 | 616.60 | 1.99 | 2.63 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 교육기관·학생수·학원/학교 인허가의 월별 공표시점 확인 |
| 고양시 | 51 | 항공 운송업 | 관리관찰 | 10,049.49 | 886.35 | 8.82 | 3.77 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 한국공항공사 GW 스케줄/공항통계 대체자료 검토 |
| 고양시 | 86 | 보건업 | 관리관찰 | 25,759.21 | 579.30 | 2.25 | 2.47 | flash_localdata_Q00_86_active_area | 0.58 | 114.09 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 46 | 도매 및 상품 중개업 | 관리관찰 | 22,666.16 | 631.21 | 2.78 | 2.69 | phase120_personal_business_sales_rows_lag2021 | 7.70 | 1,233.17 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 고양시 | 18 | 인쇄 및 기록매체 복제업 | 관리관찰 | 5,744.00 | 777.39 | 13.53 | 3.31 | flash_kosis_mfg_2021_value_added | 28.67 | 628.00 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 취약 | 후보를 바로 승격하지 말고 rolling holdout에서 재검증 |
| 고양시 | 65 | 보험 및 연금업 | 관리관찰 | 10,904.87 | 717.24 | 6.58 | 3.05 | baseline | 19.10 | 1,000.64 | baseline |  | 1.00 | baseline 유지 | 직접지표 추가 수집 전까지 baseline 유지 |
| 고양시 | 87 | 사회복지 서비스업 | 관리관찰 | 18,707.35 | 503.46 | 2.69 | 2.14 | flash_localdata_Q00_86_active_area | 3.53 | 114.09 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 84 | 공공행정 국방 및 사회보장 행정 | 관리관찰 | 28,795.92 | 261.57 | 0.91 | 1.11 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 예산집행·조달·공공고용 월별 지표 검토 |
| 고양시 | 91 | 스포츠 및 오락관련 서비스업 | 관리관찰 | 8,087.69 | 620.81 | 7.68 | 2.64 | flash_localdata_ERS_91_active_area | 1.12 | 49.01 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 저오차이나 운영개선필요 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 고양시 | 55 | 숙박업 | 관리관찰 | 5,756.59 | 553.08 | 9.61 | 2.35 | flash_고양시_I00_localdata_bundle | 0.11 | 0.35 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 63 | 정보서비스업 | 관리관찰 | 5,393.61 | 537.21 | 9.96 | 2.29 | baseline | 137.78 | 311.27 | baseline |  | 1.00 | baseline 유지 | 직접지표 추가 수집 전까지 baseline 유지 |

## 포항시 Q1 우선순위 브릿지(상위 15개 표시, 전체는 CSV 참조)

| 지역 | 중분류 | 업종명 | 금액가중 등급 | rolling 실제(억원) | rolling 오차(억원) | rolling WAPE(%) | rolling 오차기여(%) | 2023 후보 | 2023 후보 오차율(%) | 2023 후보 오차(억원) | 후보트랙 | Phase120 공개판정 | 상위그룹 일치 | 판정 | 다음 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | 68 | 부동산업 | 핵심개선 | 18,862.23 | 1,293.44 | 6.86 | 8.93 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 국토부 실거래·공시가격·건축물 공표시점 확인 후 strict 후보 생성 |
| 포항시 | 35 | 전기 가스 증기 및 공기조절 공급업 | 핵심개선 | 8,307.32 | 1,185.21 | 14.27 | 8.18 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 전력·가스 판매량/사용량 시군구 월별 공표시점 확인 |
| 포항시 | 24 | 1차 금속 제조업 | 핵심개선 | 30,595.14 | 820.18 | 2.68 | 5.66 | flash_kosis_mfg_2021_value_added | 9.90 | 4,653.51 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 저오차이나 운영개선필요 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 포항시 | 42 | 전문직별 공사업 | 핵심개선 | 24,921.20 | 750.94 | 3.01 | 5.19 | flash_building_start_area_ytd | 3.61 | 237.25 | 조건부보류 | 보류: 2셀 고적합 후보 | 1.00 | 2023 단면 저오차이나 보류 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 포항시 | 56 | 음식점 및 주점업 | 핵심개선 | 6,795.67 | 774.41 | 11.40 | 5.35 | phase120_personal_business_finance_asset_pos_lag2021 | 0.02 | 0.85 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 포항시 | 10 | 식료품 제조업 | 관리관찰 | 18,670.90 | 500.52 | 2.68 | 3.46 | flash_kosis_mfg_2021_value_added | 8.56 | 45.00 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 저오차·검증통과 | rolling nowcast 후보로만 검토, Phase145와 직접 비교 금지 |
| 포항시 | 84 | 공공행정 국방 및 사회보장 행정 | 관리관찰 | 27,667.29 | 347.69 | 1.26 | 2.40 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 예산집행·조달·공공고용 월별 지표 검토 |
| 포항시 | 85 | 교육 서비스업 | 관리관찰 | 19,234.76 | 466.48 | 2.43 | 3.22 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 교육기관·학생수·학원/학교 인허가의 월별 공표시점 확인 |
| 포항시 | 51 | 항공 운송업 | 관리관찰 | 7,780.17 | 544.67 | 7.00 | 3.76 |  |  |  | 후보없음 |  |  | 직접 as-of 후보 없음 | 한국공항공사 GW 스케줄/공항통계 대체자료 검토 |
| 포항시 | 75 | 사업지원 서비스업 | 관리관찰 | 7,076.52 | 510.34 | 7.21 | 3.52 | phase120_personal_business_finance_rows_lag2021 | 101.15 | 2,724.28 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 포항시 | 25 | 금속가공제품 제조업; 기계 및 가구 제외 | 관리관찰 | 15,277.42 | 409.55 | 2.68 | 2.83 | flash_kosis_mfg_2021_value_added | 19.17 | 524.47 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 주의 | 보조지표로 유지, 금액가중 악화 방지 gate 필요 |
| 포항시 | 47 | 소매업; 자동차 제외 | 관리관찰 | 9,706.66 | 429.13 | 4.42 | 2.96 | phase120_personal_business_sales_abs_sale_lag2021 | 0.28 | 11.17 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 포항시 | 65 | 보험 및 연금업 | 관리관찰 | 6,690.16 | 409.45 | 6.12 | 2.83 | baseline | 40.28 | 1,936.67 | baseline |  | 1.00 | baseline 유지 | 직접지표 추가 수집 전까지 baseline 유지 |
| 포항시 | 55 | 숙박업 | 관리관찰 | 3,709.92 | 370.28 | 9.98 | 2.56 | phase120_personal_business_finance_asset_pos_lag2021 | 0.19 | 0.85 | 지연구조자료 | 속보 후보: 2021 이하 지연자료 | 1.00 | 지연 구조자료 후보 | 속보 활동지표가 아니라 구조축으로만 사용 |
| 포항시 | 52 | 창고 및 운송관련 서비스업 | 관리관찰 | 5,242.98 | 372.97 | 7.11 | 2.58 | flash_localdata_H52_logistics_warehouse_capacity | 3.18 | 124.81 | 속보후보검증통과 | 속보 후보: 검증 통과 | 1.00 | 2023 단면 저오차·검증통과 | rolling nowcast 후보로만 검토, Phase145와 직접 비교 금지 |

## 직접 as-of 후보가 비어 있는 금액가중 우선순위 업종

| 지역 | 중분류 | 업종명 | 금액가중 등급 | rolling 실제(억원) | rolling 오차(억원) | rolling 오차기여(%) | 필요 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 68 | 부동산업 | 핵심개선 | 57,593.37 | 3,611.30 | 15.38 | 국토부 실거래·공시가격·건축물 공표시점 확인 후 strict 후보 생성 |
| 고양시 | 85 | 교육 서비스업 | 관리관찰 | 31,051.10 | 616.60 | 2.63 | 교육기관·학생수·학원/학교 인허가의 월별 공표시점 확인 |
| 고양시 | 51 | 항공 운송업 | 관리관찰 | 10,049.49 | 886.35 | 3.77 | 한국공항공사 GW 스케줄/공항통계 대체자료 검토 |
| 고양시 | 84 | 공공행정 국방 및 사회보장 행정 | 관리관찰 | 28,795.92 | 261.57 | 1.11 | 예산집행·조달·공공고용 월별 지표 검토 |
| 포항시 | 68 | 부동산업 | 핵심개선 | 18,862.23 | 1,293.44 | 8.93 | 국토부 실거래·공시가격·건축물 공표시점 확인 후 strict 후보 생성 |
| 포항시 | 35 | 전기 가스 증기 및 공기조절 공급업 | 핵심개선 | 8,307.32 | 1,185.21 | 8.18 | 전력·가스 판매량/사용량 시군구 월별 공표시점 확인 |
| 포항시 | 84 | 공공행정 국방 및 사회보장 행정 | 관리관찰 | 27,667.29 | 347.69 | 2.40 | 예산집행·조달·공공고용 월별 지표 검토 |
| 포항시 | 85 | 교육 서비스업 | 관리관찰 | 19,234.76 | 466.48 | 3.22 | 교육기관·학생수·학원/학교 인허가의 월별 공표시점 확인 |
| 포항시 | 51 | 항공 운송업 | 관리관찰 | 7,780.17 | 544.67 | 3.76 | 한국공항공사 GW 스케줄/공항통계 대체자료 검토 |

## as-of 후보가 있으나 아직 약한 업종

| 지역 | 중분류 | 업종명 | 금액가중 등급 | 2023 후보 | 2023 후보 오차율(%) | 2023 후보 오차(억원) | 필요 조치 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 42 | 전문직별 공사업 | 핵심개선 | flash_building_start_area_ytd | 0.01 | 0.75 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 56 | 음식점 및 주점업 | 관리관찰 | flash_고양시_I00_localdata_bundle | 0.00 | 0.35 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 86 | 보건업 | 관리관찰 | flash_localdata_Q00_86_active_area | 0.58 | 114.09 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 18 | 인쇄 및 기록매체 복제업 | 관리관찰 | flash_kosis_mfg_2021_value_added | 28.67 | 628.00 | 후보를 바로 승격하지 말고 rolling holdout에서 재검증 |
| 고양시 | 87 | 사회복지 서비스업 | 관리관찰 | flash_localdata_Q00_86_active_area | 3.53 | 114.09 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 91 | 스포츠 및 오락관련 서비스업 | 관리관찰 | flash_localdata_ERS_91_active_area | 1.12 | 49.01 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 고양시 | 55 | 숙박업 | 관리관찰 | flash_고양시_I00_localdata_bundle | 0.11 | 0.35 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 고양시 | 10 | 식료품 제조업 | 관리관찰 | flash_kosis_mfg_2021_value_added | 69.49 | 754.32 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 포항시 | 24 | 1차 금속 제조업 | 핵심개선 | flash_kosis_mfg_2021_value_added | 9.90 | 4,653.51 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 포항시 | 42 | 전문직별 공사업 | 핵심개선 | flash_building_start_area_ytd | 3.61 | 237.25 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 포항시 | 25 | 금속가공제품 제조업; 기계 및 가구 제외 | 관리관찰 | flash_kosis_mfg_2021_value_added | 19.17 | 524.47 | 보조지표로 유지, 금액가중 악화 방지 gate 필요 |
| 포항시 | 41 | 종합 건설업 | 관리관찰 | flash_building_start_area_ytd | 1.88 | 237.25 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 포항시 | 50 | 수상 운송업 | 관리관찰 | flash_localdata_H52_logistics_warehouse_capacity | 60.53 | 574.22 | 후보를 바로 승격하지 말고 rolling holdout에서 재검증 |
| 포항시 | 86 | 보건업 | 관리관찰 | flash_localdata_Q00_86_active_area | 0.14 | 12.06 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |
| 포항시 | 34 | 산업용 기계 및 장비 수리업 | 관리관찰 | flash_kosis_mfg_2021_value_added | 255.23 | 1,286.21 | 저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요 |
| 포항시 | 29 | 기타 기계 및 장비 제조업 | 관리관찰 | flash_kosis_mfg_2021_value_added | 48.81 | 577.38 | 후보를 바로 승격하지 말고 rolling holdout에서 재검증 |
| 포항시 | 87 | 사회복지 서비스업 | 관리관찰 | flash_localdata_Q00_86_active_area | 0.67 | 12.06 | 2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout |

## 무료 API·파일 후보

| 우선순위 | 대상 업종 | 자료명 | 링크 | 활용 목적 | 키/신청 | 포괄 한계 | 공표시차 상태 | 확인일 | as-of 적격성 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 상 | 부동산업 | 국토교통부_아파트매매 실거래 상세 자료 | https://www.data.go.kr/data/15126469/openapi.do | 부동산 GVA의 거래활동·가격·회전율 활동지표 | 기존 공공데이터포털 키로 가능 여부 확인 | 아파트 거래 중심. 부동산업 전체 GVA를 직접 대표하지 않음 | 공표시차 원문 확인 필요 | 2026-07-26 | 미확정 |
| 상 | 항공 운송업 | 한국공항공사_항공기 운항 스케줄 정보_GW | https://www.data.go.kr/data/15158949/openapi.do | 김포공항/인접 공항 운항·노선 빈도 활동지표 | 공공데이터포털 활용신청 필요 가능 | 스케줄 자료이며 실제 여객·화물 실적과 다를 수 있음 | 실시간으로 표기되나 과거 as-of 재현 가능성 확인 필요 | 2026-07-26 | 미확정 |
| 중 | 관광·숙박·문화 | 한국관광공사_국문 관광정보 서비스_GW | https://www.data.go.kr/data/15101578/openapi.do | 관광·숙박 시설 구조지표 및 지역 관광활동 보조 | 공공데이터포털 활용신청 필요 가능 | 관광 콘텐츠/시설 중심. 숙박·문화 GVA 직접 활동량은 아님 | 실시간으로 표기되나 GVA 예측용 공표시차 별도 확인 필요 | 2026-07-26 | 미확정 |
| 중 | 항공 운송업 | 한국공항공사_항공사별 운항실적 파일데이터 | https://www.data.go.kr/data/15002628/fileData.do | 연간 운항실적 구조자료. 속보성은 약하지만 정밀화 보조 가능 | 파일데이터라 별도 API 키 불필요 가능 | 연간 파일자료. Q+1개월 속보에는 부적합할 가능성 큼 | 연간 업데이트 | 2026-07-26 | 정밀화 보조 |

확인한 공개 후보는 모두 무료 공개자료 계열이다. 다만 공공데이터포털 API는 활용신청 또는 기존 key 적용 가능 여부 확인이 필요하다.

## 판정

1. 현재 운영 성능 주장은 Phase145 기준으로 유지한다. Phase120 strict/as-of 후보는 아직 rolling 운영 성능으로 승격하지 않는다.
2. 고양시는 부동산업·항공 운송업·교육 서비스업처럼 금액가중 우선순위가 높지만 직접 as-of 후보가 없는 업종이 남아 있다.
3. 포항시는 부동산업·전기/가스/공기조절 공급업·항공 운송업·교육 서비스업·공공행정이 직접 as-of 후보 공백이다.
4. as-of 후보가 있는 업종도 2023 단면에서만 좋게 보이면 안 된다. 다음 단계는 Phase145 rolling 구조에 후보를 넣고 2022~2023 또는 추가연도 holdout에서만 채택하는 것이다.
5. 부동산업은 두 도시 모두 금액가중 중요도가 크고 직접 후보가 비어 있으므로, 다음 개선 실험의 1순위다.

## 다음 실험

1. 고양·포항 부동산업에 대해 국토부 실거래 API와 기존 로컬 실거래 manifest의 공표시점/as-of 적격성을 다시 감사한다.
2. 실거래 자료가 Q+1개월 strict로 인정되는 범위만 사용해 부동산업 annual nowcast 후보를 만든다.
3. 후보는 Phase145 baseline과 같은 rolling-origin 방식으로만 비교한다.
4. 항공 운송업은 한국공항공사 GW 스케줄 API 또는 항공통계 파일을 수집할 수 있는지 확인한 뒤 동일 절차를 적용한다.

## Phase132 공표일자 확인 요청 일부

| source_id | source_label | city | source_family | native_period_min | native_period_max | release_date | release_rule | timing_track_local | strict_flash_class | precision_class | reason | evidence_file | request_to_user |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| flash_building_permit_area_ytd | 고양시 허가면적 누적 | 고양시 | F00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_building_permit_area_ytd | 고양시 허가면적 누적 | 고양시 | F00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_building_start_area_ytd | 고양시 착공면적 누적 | 고양시 | F00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_building_start_area_ytd | 고양시 착공면적 누적 | 고양시 | F00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_goyang_bus_passenger_ytd | 고양 버스 승하차 누적 | 고양시 | H00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_goyang_bus_passenger_ytd | 고양 버스 승하차 누적 | 고양시 | H00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_90_active_area | 고양시 인허가 영업면적 90 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_90_active_area | 고양시 인허가 영업면적 90 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_90_active_count | 고양시 인허가 영업재고 90 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_90_active_count | 고양시 인허가 영업재고 90 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_91_active_area | 고양시 인허가 영업면적 91 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_91_active_area | 고양시 인허가 영업면적 91 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_91_active_count | 고양시 인허가 영업재고 91 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_91_active_count | 고양시 인허가 영업재고 91 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_96_active_area | 고양시 인허가 영업면적 96 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_96_active_area | 고양시 인허가 영업면적 96 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_96_active_count | 고양시 인허가 영업재고 96 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_ERS_96_active_count | 고양시 인허가 영업재고 96 | 고양시 | ERS |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_G00_47_active_area | 고양시 인허가 영업면적 47 | 고양시 | G00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase117_max_source_flash_push/phase117_flash_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
| flash_localdata_G00_47_active_area | 고양시 인허가 영업면적 47 | 고양시 | G00 |  |  |  |  | 속보성 | needs_publication_calendar | usable_after_publication | 속보성 후보지만 원 공표일자/시차 확인 필요 | /Users/bellhundred/git-repo/denton/data/processed/phase120_finance_procurement_source_integration/phase120_all_candidate_indicators.csv | 원 출처의 과거 공표일자 또는 as-of archive 확인 필요 |
