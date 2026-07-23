# Phase127 Phase114 정밀 기준 COMWEL 재평가

## 목적

COMWEL 사업장 자료를 속보 경로가 아니라 Phase114 정밀 기준 위에서 다시 평가했다. 자료 시점상 정밀화 전용 후보로만 해석한다.

## 무악화 선택 결과

| city | base error 억원 | base wape % | phase127 strict error 억원 | phase127 strict wape % | reduction 억원 | base gt20 cells | phase127 strict gt20 cells | base gt10 cells | phase127 strict gt10 cells | worsened cells | worsen sum 억원 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 5,202.32 | 3.07 | 5,114.68 | 3.02 | 87.64 | 8 | 8 | 17 | 17 | 0 | 0.00 |
| 포항시 | 9,065.93 | 5.87 | 7,718.22 | 5.00 | 1,347.71 | 15 | 15 | 21 | 21 | 0 | 0.00 |

## 리스크 예산 선택 결과

| city | base error 억원 | base wape % | phase127 risk error 억원 | phase127 risk wape % | reduction 억원 | base gt20 cells | phase127 risk gt20 cells | base gt10 cells | phase127 risk gt10 cells | worsened cells | worsen sum 억원 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | 5,202.32 | 3.07 | 4,795.57 | 2.83 | 406.74 | 8 | 7 | 17 | 16 | 3 | 123.65 |
| 포항시 | 9,065.93 | 5.87 | 7,278.52 | 4.71 | 1,787.41 | 15 | 14 | 21 | 20 | 1 | 0.48 |

## 무악화 채택 후보

| city | parent code | block id | middle codes | metric label | alpha | baseline floor | error reduction 억원 | base gt10 cells | candidate gt10 cells | worsened cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | F00 | F00_all | 41,42 | 고용보험 상시근로자수 | 0.25 | 0.00 | 1,026.87 | 0 | 0 | 0 |
| 포항시 | Q00 | Q00_all | 86,87 | 고용보험 상시근로자수 | 0.05 | 0.20 | 307.48 | 0 | 0 | 0 |
| 고양시 | MN0 | facility_support_74_76 | 74,75,76 | 고용보험 상시근로자수 | 0.08 | 0.60 | 72.58 | 0 | 0 | 0 |
| 고양시 | G00 | G00_all | 45,46,47 | 고용보험 상시근로자수 | 0.02 | 0.80 | 15.06 | 0 | 0 | 0 |
| 포항시 | I00 | I00_all | 55,56 | 고용보험 상시근로자수 | 0.05 | 0.10 | 7.20 | 0 | 0 | 0 |
| 포항시 | ERS | culture_leisure_90_91 | 90,91 | 산재보험 상시근로자수 | 0.20 | 0.10 | 6.16 | 0 | 0 | 0 |

## 리스크 예산 채택 후보

| city | parent code | block id | middle codes | metric label | alpha | baseline floor | error reduction 억원 | base gt20 cells | candidate gt20 cells | base gt10 cells | candidate gt10 cells | worsened cells | worsen sum 억원 | max worsen pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | MN0 | facility_support_74_76 | 74,75,76 | 사업장수 | 0.33 | 0.10 | 453.06 | 1 | 0 | 2 | 1 | 1 | 0.48 | 0.08 |
| 고양시 | J00 | content_58_60 | 58,59,60 | 산재보험 상시근로자수 | 1.00 | 0.20 | 145.78 | 2 | 1 | 2 | 1 | 1 | 51.05 | 5.35 |
| 포항시 | F00 | F00_all | 41,42 | 고용보험 상시근로자수 | 0.25 | 0.00 | 1,026.87 | 0 | 0 | 0 | 0 | 0 | 0.00 | -4.07 |
| 포항시 | Q00 | Q00_all | 86,87 | 고용보험 상시근로자수 | 0.05 | 0.20 | 307.48 | 0 | 0 | 0 | 0 | 0 | 0.00 | -1.76 |
| 고양시 | MN0 | facility_support_74_76 | 74,75,76 | 고용보험 상시근로자수 | 0.08 | 0.60 | 72.58 | 0 | 0 | 0 | 0 | 0 | 0.00 | -0.11 |
| 고양시 | G00 | G00_all | 45,46,47 | 고용보험 상시근로자수 | 0.25 | 0.80 | 130.61 | 0 | 0 | 0 | 0 | 1 | 36.82 | 0.23 |
| 고양시 | K00 | K00_all | 64,65,66 | 사업장수 | 0.01 | 0.20 | 57.77 | 0 | 0 | 0 | 0 | 1 | 35.77 | 0.68 |

## 리스크 기준 개선 셀

| city | parent code | middle code | middle label | actual gva 억원 | phase127 base error gva 억원 | phase127 risk error gva 억원 | phase127 risk error rate % | phase127 risk reduction vs base 억원 | phase127 risk option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | F00 | 41 | 종합 건설업 | 12,603.38 | 516.59 | 3.16 | 0.03 | 513.43 | phase127_comwel_employment_workers_F00_all |
| 포항시 | F00 | 42 | 전문직별 공사업 | 6,565.34 | 516.59 | 3.16 | 0.05 | 513.43 | phase127_comwel_employment_workers_F00_all |
| 포항시 | MN0 | 74 | 사업시설 관리 및 조경 서비스업 | 1,421.27 | 390.23 | 129.65 | 9.12 | 260.58 | phase127_comwel_workplace_count_facility_support_74_76 |
| 포항시 | MN0 | 75 | 사업지원 서비스업 | 2,693.30 | 226.53 | 33.57 | 1.25 | 192.96 | phase127_comwel_workplace_count_facility_support_74_76 |
| 고양시 | J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 319.38 | 144.14 | 9.83 | 175.24 | phase127_comwel_industrial_workers_content_58_60 |
| 포항시 | Q00 | 87 | 사회복지 서비스업 | 1,795.00 | 157.93 | 4.19 | 0.23 | 153.74 | phase127_comwel_employment_workers_Q00_all |
| 포항시 | Q00 | 86 | 보건업 | 8,754.86 | 157.93 | 4.19 | 0.05 | 153.74 | phase127_comwel_employment_workers_Q00_all |
| 고양시 | G00 | 47 | 소매업 | 12,778.67 | 110.42 | 5.79 | 0.05 | 104.64 | phase127_comwel_employment_workers_G00_all |
| 고양시 | K00 | 66 | 금융·보험 관련 서비스업 | 1,473.92 | 111.58 | 46.92 | 3.18 | 64.65 | phase127_comwel_workplace_count_K00_all |
| 고양시 | G00 | 45 | 자동차·부품 판매업 | 2,304.83 | 107.92 | 45.12 | 1.96 | 62.80 | phase127_comwel_employment_workers_G00_all |
| 고양시 | MN0 | 76 | 임대업 | 1,610.20 | 48.22 | 5.38 | 0.33 | 42.84 | phase127_comwel_employment_workers_facility_support_74_76 |
| 고양시 | K00 | 64 | 금융업 | 6,909.30 | 174.92 | 146.04 | 2.11 | 28.88 | phase127_comwel_workplace_count_K00_all |
| 고양시 | MN0 | 74 | 사업시설 관리업 | 1,389.38 | 31.76 | 6.55 | 0.47 | 25.20 | phase127_comwel_employment_workers_facility_support_74_76 |
| 고양시 | J00 | 58 | 출판업 | 2,524.21 | 123.94 | 102.35 | 4.05 | 21.60 | phase127_comwel_industrial_workers_content_58_60 |
| 고양시 | MN0 | 75 | 사업지원 서비스업 | 4,277.03 | 68.07 | 63.53 | 1.49 | 4.53 | phase127_comwel_employment_workers_facility_support_74_76 |

## 남은 10% 초과 셀

| city | parent code | middle code | middle label | actual gva 억원 | phase127 risk predicted gva 억원 | phase127 risk error gva 억원 | phase127 risk error rate % | phase127 risk option id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 고양시 | ERS | 94 | 협회·단체 | 990.96 | 1,775.00 | 784.03 | 79.12 | phase114_precision_base |
| 고양시 | ERS | 91 | 스포츠·오락 서비스업 | 4,365.64 | 3,634.49 | 731.16 | 16.75 | phase114_precision_base |
| 고양시 | J00 | 60 | 방송업 | 954.74 | 496.85 | 457.89 | 47.96 | phase127_comwel_industrial_workers_content_58_60 |
| 고양시 | C00 | 14 | 의복·모피 제조업 | 977.21 | 728.74 | 248.47 | 25.43 | phase114_precision_base |
| 고양시 | MN0 | 70 | 연구개발업 | 1,920.21 | 2,143.65 | 223.45 | 11.64 | phase114_precision_base |
| 고양시 | MN0 | 73 | 과학기술 서비스업 | 968.98 | 809.37 | 159.62 | 16.47 | phase114_precision_base |
| 고양시 | C00 | 15 | 가죽·가방·신발 제조업 | 572.01 | 418.43 | 153.58 | 26.85 | phase114_precision_base |
| 고양시 | J00 | 62 | 컴퓨터·시스템통합업 | 750.55 | 892.10 | 141.55 | 18.86 | phase114_precision_base |
| 고양시 | C00 | 10 | 식료품 제조업 | 1,085.48 | 1,198.24 | 112.76 | 10.39 | phase114_precision_base |
| 고양시 | C00 | 20 | 화학물질·화학제품 제조업 | 723.76 | 620.67 | 103.08 | 14.24 | phase114_precision_base |
| 고양시 | ERS | 37 | 하수·폐수 처리업 | 444.87 | 353.08 | 91.79 | 20.63 | phase114_precision_base |
| 고양시 | C00 | 34 | 산업용 기계 수리업 | 388.16 | 447.03 | 58.87 | 15.17 | phase114_precision_base |
| 고양시 | ERS | 36 | 수도업 | 377.33 | 416.27 | 38.94 | 10.32 | phase114_precision_base |
| 고양시 | C00 | 21 | 의약품 제조업 | 69.97 | 102.97 | 33.00 | 47.16 | phase114_precision_base |
| 고양시 | C00 | 30 | 자동차·트레일러 제조업 | 159.83 | 190.31 | 30.48 | 19.07 | phase114_precision_base |
| 고양시 | H00 | 50 | 수상 운송업 | 35.94 | 22.03 | 13.91 | 38.71 | phase114_precision_base |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.33 | 3,567.79 | 1,032.46 | 40.72 | phase114_precision_base |
| 포항시 | K00 | 65 | 보험 및 연금업 | 4,807.52 | 4,114.05 | 693.47 | 14.42 | phase114_precision_base |
| 포항시 | K00 | 66 | 금융 및 보험 관련 서비스업 | 859.14 | 1,268.31 | 409.17 | 47.63 | phase114_precision_base |
| 포항시 | C00 | 28 | 전기장비 제조업 | 971.67 | 585.54 | 386.13 | 39.74 | phase114_precision_base |
| 포항시 | ERS | 96 | 기타 개인 서비스업 | 910.66 | 1,260.62 | 349.96 | 38.43 | phase114_precision_base |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.93 | 169.34 | 334.59 | 66.40 | phase114_precision_base |
| 포항시 | K00 | 64 | 금융업 | 2,788.74 | 3,073.03 | 284.30 | 10.19 | phase114_precision_base |
| 포항시 | ERS | 36 | 수도업 | 439.72 | 267.40 | 172.32 | 39.19 | phase114_precision_base |
| 포항시 | ERS | 37 | 하수 폐수 및 분뇨 처리업 | 296.03 | 159.05 | 136.99 | 46.27 | phase114_precision_base |
| 포항시 | MN0 | 76 | 임대업; 부동산 제외 | 635.20 | 543.81 | 91.39 | 14.39 | phase127_comwel_workplace_count_facility_support_74_76 |
| 포항시 | J00 | 60 | 방송업 | 386.79 | 304.82 | 81.98 | 21.19 | phase114_precision_base |
| 포항시 | MN0 | 73 | 기타 전문 과학 및 기술 서비스업 | 120.05 | 192.38 | 72.32 | 60.24 | phase114_precision_base |
| 포항시 | J00 | 62 | 컴퓨터 프로그래밍 시스템 통합 및 관리업 | 194.64 | 266.36 | 71.72 | 36.85 | phase114_precision_base |
| 포항시 | C00 | 31 | 기타 운송장비 제조업 | 255.79 | 295.58 | 39.79 | 15.56 | phase114_precision_base |
| 포항시 | C00 | 16 | 목재 및 나무제품 제조업; 가구 제외 | 60.44 | 85.92 | 25.48 | 42.15 | phase114_precision_base |
| 포항시 | C00 | 22 | 고무 및 플라스틱제품 제조업 | 101.94 | 123.26 | 21.32 | 20.91 | phase114_precision_base |
| 포항시 | ERS | 39 | 환경 정화 및 복원업 | 34.85 | 14.63 | 20.22 | 58.01 | phase114_precision_base |
| 포항시 | J00 | 59 | 영상ㆍ오디오 기록물 제작 및 배급업 | 139.78 | 120.92 | 18.86 | 13.50 | phase114_precision_base |
| 포항시 | C00 | 30 | 자동차 및 트레일러 제조업 | 104.53 | 116.84 | 12.31 | 11.77 | phase114_precision_base |
| 포항시 | J00 | 63 | 정보서비스업 | 3.95 | 13.83 | 9.88 | 250.49 | phase114_precision_base |

## 판정

Phase114 정밀 기준은 이미 강해서 COMWEL의 추가 기여는 제한적이다. 무악화 후보는 공모전 최종 성능에 넣어도 비교적 안전하지만, 리스크 예산 후보는 일부 셀 악화를 동반하므로 내부 개선 후보로만 분리하는 편이 좋다.
