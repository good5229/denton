# Phase126 리스크 예산형 COMWEL 후보 채택 실험

## 목적

Phase125의 무악화 기준에서 탈락한 후보 중, 총오차와 20% 초과 셀을 줄이면서 악화폭이 수치적으로 작게 통제되는 후보만 제한적으로 채택했다.

COMWEL 자료는 2025-12-31 사업장 스냅샷이므로 이 단계 역시 **정밀화/구조 개선 후보**이며 속보성 지표로 주장하지 않는다.

## 리스크 예산

- 후보 블록 총오차 감소: 100억원 이상
- 20% 초과 셀 수 증가 금지
- 10% 초과 셀 수 증가 금지
- 악화 셀: 1개 이하
- 악화합계: 200억원 이하
- 최대 악화: 12%p 이하

## 도시별 성능

| city | phase124 error 억원 | phase124 wape % | phase125 error 억원 | phase125 wape % | phase126 error 억원 | phase126 wape % | reduction vs phase125 억원 | phase125 gt20 cells | phase126 gt20 cells | worsened vs phase125 cells | worsened vs phase125 sum 억원 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 26,951.63 | 15.91 | 26,039.44 | 15.37 | 25,033.35 | 14.78 | 1,006.09 | 29 | 29 | 3 | 290.63 |
| 포항시 | 34,126.07 | 22.09 | 33,660.75 | 21.79 | 32,467.67 | 21.02 | 1,193.08 | 30 | 28 | 1 | 18.03 |

## 추가 채택 후보

| city | parent code | block id | middle codes | metric label | alpha | baseline floor | incremental reduction 억원 | phase124 gt20 cells | candidate gt20 cells | worsened cells | worsen sum 억원 | max worsen pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | C00 | mfg_equipment_26_34 | 27,28,29,30,31,34 | 사업장수 | 0.67 | 0.40 | 1,193.08 | 5 | 3 | 1 | 18.03 | 9.81 |
| 고양시 | MN0 | professional_70_73 | 70,71,72,73 | 고용보험 상시근로자수 | 0.10 | 0.00 | 120.66 | 2 | 2 | 1 | 68.01 | 1.66 |
| 고양시 | G00 | G00_all | 45,46,47 | 고용보험 상시근로자수 | 0.33 | 0.60 | 105.34 | 0 | 0 | 1 | 154.57 | 1.21 |
| 고양시 | J00 | content_58_60 | 58,59,60 | 산재보험 상시근로자수 | 1.00 | 0.00 | 780.09 | 3 | 3 | 1 | 68.05 | 4.64 |

## 변화 중분류

| city | parent code | middle code | middle label | actual gva 억원 | phase125 error gva 억원 | phase126 error gva 억원 | phase126 error rate % | phase126 incremental reduction vs phase125 억원 | phase126 option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.93 | 1,286.21 | 733.36 | 145.53 | 552.85 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | C00 | 29 | 기타 기계 및 장비 제조업 | 1,182.91 | 577.38 | 73.49 | 6.21 | 503.88 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 고양시 | J00 | 58 | 출판업 | 2,524.21 | 1,252.48 | 794.38 | 31.47 | 458.10 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | J00 | 60 | 방송업 | 954.74 | 746.05 | 356.00 | 37.29 | 390.05 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | G00 | 45 | 자동차·부품 판매업 | 2,304.83 | 421.89 | 214.65 | 9.31 | 207.24 | phase125_comwel_employment_workers_G00_all |
| 포항시 | C00 | 28 | 전기장비 제조업 | 971.67 | 112.14 | 18.70 | 1.92 | 93.45 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 고양시 | MN0 | 72 | 건축·엔지니어링 서비스업 | 2,345.78 | 311.82 | 233.74 | 9.96 | 78.08 | phase125_comwel_employment_workers_professional_70_73 |
| 고양시 | MN0 | 73 | 과학기술 서비스업 | 968.98 | 858.38 | 798.05 | 82.36 | 60.33 | phase125_comwel_employment_workers_professional_70_73 |
| 고양시 | G00 | 46 | 도매·상품중개업 | 16,007.70 | 1,233.17 | 1,180.50 | 7.37 | 52.67 | phase125_comwel_employment_workers_G00_all |
| 고양시 | MN0 | 70 | 연구개발업 | 1,920.21 | 1,405.36 | 1,355.10 | 70.57 | 50.25 | phase125_comwel_employment_workers_professional_70_73 |
| 포항시 | C00 | 31 | 기타 운송장비 제조업 | 255.79 | 92.65 | 47.55 | 18.59 | 45.11 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.53 | 96.47 | 80.65 | 77.15 | 15.82 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | C00 | 27 | 의료 정밀 광학기기 및 시계 제조업 | 183.75 | 143.20 | 161.23 | 87.74 | -18.03 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 고양시 | MN0 | 71 | 전문 서비스업 | 4,106.09 | 205.54 | 273.55 | 6.66 | -68.01 | phase125_comwel_employment_workers_professional_70_73 |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 403.49 | 471.54 | 32.14 | -68.05 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | G00 | 47 | 소매업 | 12,778.67 | 811.28 | 965.86 | 7.56 | -154.57 | phase125_comwel_employment_workers_G00_all |

## 남은 20% 초과 중분류

| city | parent code | middle code | middle label | actual gva 억원 | phase126 predicted gva 억원 | phase126 error gva 억원 | phase126 error rate % | phase126 option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | K00 | 66 | 금융·보험 관련 서비스업 | 1,473.92 | 3,257.28 | 1,783.35 | 120.99 | baseline |
| 고양시 | J00 | 61 | 우편·통신업 | 3,000.54 | 1,232.91 | 1,767.63 | 58.91 | baseline |
| 고양시 | ERS | 96 | 기타 개인 서비스업 | 2,465.53 | 3,868.64 | 1,403.12 | 56.91 | phase125_comwel_employment_workers_association_personal_94_96 |
| 고양시 | MN0 | 70 | 연구개발업 | 1,920.21 | 565.10 | 1,355.10 | 70.57 | phase125_comwel_employment_workers_professional_70_73 |
| 고양시 | ERS | 38 | 폐기물 처리·재생업 | 1,408.65 | 300.11 | 1,108.54 | 78.70 | flash_localdata_ERS_91_active_area |
| 고양시 | MN0 | 73 | 과학기술 서비스업 | 968.98 | 1,767.03 | 798.05 | 82.36 | phase125_comwel_employment_workers_professional_70_73 |
| 고양시 | J00 | 58 | 출판업 | 2,524.21 | 3,318.59 | 794.38 | 31.47 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | C00 | 10 | 식료품 제조업 | 1,085.48 | 1,839.80 | 754.32 | 69.49 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 18 | 인쇄·기록매체 복제업 | 2,190.69 | 2,818.69 | 628.00 | 28.67 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 33 | 기타 제품 제조업 | 1,035.80 | 1,582.48 | 546.68 | 52.78 | flash_kosis_mfg_2021_value_added |
| 고양시 | J00 | 62 | 컴퓨터·시스템통합업 | 750.55 | 1,296.99 | 546.44 | 72.81 | baseline |
| 고양시 | C00 | 23 | 비금속 광물제품 제조업 | 1,153.87 | 628.33 | 525.53 | 45.55 | flash_kosis_mfg_2021_value_added |
| 고양시 | ERS | 94 | 협회·단체 | 990.96 | 1,505.94 | 514.98 | 51.97 | phase125_comwel_employment_workers_association_personal_94_96 |
| 고양시 | C00 | 26 | 전자부품·컴퓨터 제조업 | 1,022.76 | 539.66 | 483.10 | 47.24 | flash_kosis_mfg_2021_value_added |
| 고양시 | ERS | 90 | 창작·예술 서비스업 | 1,141.86 | 659.92 | 481.94 | 42.21 | phase125_comwel_workplace_count_culture_leisure_90_91 |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 1,938.55 | 471.54 | 32.14 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | C00 | 14 | 의복·모피 제조업 | 977.21 | 589.26 | 387.95 | 39.70 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 32 | 가구 제조업 | 612.12 | 996.16 | 384.04 | 62.74 | flash_kosis_mfg_2021_value_added |
| 고양시 | J00 | 60 | 방송업 | 954.74 | 598.74 | 356.00 | 37.29 | phase125_comwel_industrial_workers_content_58_60 |
| 고양시 | ERS | 37 | 하수·폐수 처리업 | 444.87 | 92.71 | 352.16 | 79.16 | flash_localdata_ERS_91_active_area |
| 고양시 | ERS | 36 | 수도업 | 377.33 | 49.85 | 327.48 | 86.79 | flash_localdata_ERS_91_active_area |
| 고양시 | J00 | 63 | 정보서비스업 | 225.92 | 537.19 | 311.27 | 137.78 | baseline |
| 고양시 | MN0 | 74 | 사업시설 관리업 | 1,389.38 | 1,681.76 | 292.38 | 21.04 | phase120_personal_business_sales_rows_lag2021 |
| 고양시 | C00 | 15 | 가죽·가방·신발 제조업 | 572.01 | 339.16 | 232.85 | 40.71 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 498.80 | 224.95 | 31.08 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 16 | 목재·나무제품 제조업 | 205.93 | 397.40 | 191.48 | 92.98 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 13 | 섬유제품 제조업 | 786.62 | 622.64 | 163.98 | 20.85 | flash_kosis_mfg_2021_value_added |
| 고양시 | C00 | 21 | 의약품 제조업 | 69.97 | 115.93 | 45.96 | 65.68 | flash_kosis_mfg_2021_value_added |
| 고양시 | H00 | 50 | 수상 운송업 | 35.94 | 10.05 | 25.90 | 72.05 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | MN0 | 71 | 전문 서비스업 | 8,942.96 | 3,113.79 | 5,829.18 | 65.18 | phase125_comwel_workplace_count_professional_70_73 |
| 포항시 | MN0 | 75 | 사업지원 서비스업 | 2,693.30 | 5,417.58 | 2,724.28 | 101.15 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | K00 | 65 | 보험 및 연금업 | 4,807.52 | 2,870.85 | 1,936.67 | 40.28 | baseline |
| 포항시 | ERS | 96 | 기타 개인 서비스업 | 910.66 | 2,664.91 | 1,754.25 | 192.63 | phase120_personal_business_finance_abs_sale_lag2021 |
| 포항시 | ERS | 38 | 폐기물 수집 운반 처리 및 원료 재생업 | 2,001.00 | 307.53 | 1,693.47 | 84.63 | phase120_personal_business_finance_abs_sale_lag2021 |
| 포항시 | MN0 | 76 | 임대업; 부동산 제외 | 635.20 | 1,735.56 | 1,100.37 | 173.23 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.33 | 3,558.61 | 1,023.29 | 40.36 | phase125_comwel_workplace_count_professional_70_73 |
| 포항시 | K00 | 64 | 금융업 | 2,788.74 | 3,802.27 | 1,013.54 | 36.34 | baseline |
| 포항시 | MN0 | 74 | 사업시설 관리 및 조경 서비스업 | 1,421.27 | 2,405.11 | 983.84 | 69.22 | phase120_personal_business_finance_rows_lag2021 |
| 포항시 | J00 | 61 | 우편 및 통신업 | 1,816.77 | 862.29 | 954.48 | 52.54 | baseline |
| 포항시 | K00 | 66 | 금융 및 보험 관련 서비스업 | 859.14 | 1,782.27 | 923.13 | 107.45 | baseline |
| 포항시 | C00 | 23 | 비금속 광물제품 제조업 | 3,822.89 | 2,965.79 | 857.09 | 22.42 | flash_kosis_mfg_2021_value_added |
| 포항시 | MN0 | 70 | 연구개발업 | 1,642.92 | 870.72 | 772.19 | 47.00 | phase125_comwel_workplace_count_professional_70_73 |
| 포항시 | MN0 | 73 | 기타 전문 과학 및 기술 서비스업 | 120.05 | 889.65 | 769.60 | 641.04 | phase125_comwel_workplace_count_professional_70_73 |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.93 | 1,237.29 | 733.36 | 145.53 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | H00 | 50 | 수상 운송업 | 948.61 | 374.39 | 574.22 | 60.53 | flash_localdata_H52_logistics_warehouse_capacity |
| 포항시 | J00 | 58 | 출판업 | 224.06 | 768.32 | 544.26 | 242.91 | baseline |
| 포항시 | ERS | 94 | 협회 및 단체 | 519.09 | 949.03 | 429.94 | 82.83 | phase120_personal_business_finance_abs_sale_lag2021 |
| 포항시 | ERS | 36 | 수도업 | 439.72 | 53.39 | 386.33 | 87.86 | phase120_personal_business_finance_abs_sale_lag2021 |
| 포항시 | J00 | 62 | 컴퓨터 프로그래밍 시스템 통합 및 관리업 | 194.64 | 567.44 | 372.79 | 191.53 | baseline |
| 포항시 | ERS | 37 | 하수 폐수 및 분뇨 처리업 | 296.03 | 82.16 | 213.88 | 72.25 | phase120_personal_business_finance_abs_sale_lag2021 |
| 포항시 | C00 | 27 | 의료 정밀 광학기기 및 시계 제조업 | 183.75 | 344.98 | 161.23 | 87.74 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | J00 | 60 | 방송업 | 386.79 | 266.15 | 120.64 | 31.19 | baseline |
| 포항시 | J00 | 59 | 영상ㆍ오디오 기록물 제작 및 배급업 | 139.78 | 230.74 | 90.96 | 65.08 | baseline |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.53 | 185.18 | 80.65 | 77.15 | phase125_comwel_workplace_count_mfg_equipment_26_34 |
| 포항시 | J00 | 63 | 정보서비스업 | 3.95 | 71.05 | 67.10 | 1,700.53 | baseline |
| 포항시 | C00 | 17 | 펄프 종이 및 종이제품 제조업 | 96.15 | 45.79 | 50.36 | 52.38 | flash_kosis_mfg_2021_value_added |
| 포항시 | ERS | 39 | 환경 정화 및 복원업 | 34.85 | 10.65 | 24.20 | 69.45 | phase120_personal_business_finance_abs_sale_lag2021 |

## 판정

리스크 예산형 선택은 무악화 방식보다 포항 제조업 일부를 더 개선할 수 있지만, 고양·포항 전체 취약 업종을 20% 이내로 끌어내리기에는 부족하다. 다음 단계는 남은 대형 오차 업종별 직접 활동자료 확보 또는 도시 특화 보조자료가 필요하다.
